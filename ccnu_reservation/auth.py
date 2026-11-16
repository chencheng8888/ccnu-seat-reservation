"""CAS login: student credentials -> handoff token -> Session Token."""

import http.cookiejar
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from .errors import InvalidCredentials, LoginFailed, UpstreamBlocked
from .transport import (
    JSQ_BASE_URL,
    REM_BASE_URL,
    USER_AGENT,
    ApiClient,
)

SEAT_RESERVATION_PROJECT_ID = "1981289670190006272"
PORTAL_TIMEOUT = 25

_ACCEPT_HTML = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
_ACCEPT_LANGUAGE = "zh-CN,zh;q=0.9"
_GOTO_PATTERN = re.compile(r"/rem/static/gotoProject/(\d+)")


class _CasFormParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}
        self.form_actions = {}
        self.first_action = ""

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            action = attributes.get("action") or ""
            if action:
                if not self.first_action:
                    self.first_action = action
                form_id = attributes.get("id")
                if form_id:
                    self.form_actions[form_id] = action
        elif tag == "input":
            name = attributes.get("name")
            if name and "value" in attributes:
                self.values[name] = attributes.get("value") or ""


def parse_cas_form(html):
    parser = _CasFormParser()
    parser.feed(html)
    lt = parser.values.get("lt", "")
    execution = parser.values.get("execution", "")
    action = parser.form_actions.get("fm1") or parser.first_action
    if not lt or not execution or not action:
        raise LoginFailed("CAS 登录表单无法识别，登录页可能已改版")
    return lt, execution, action


def find_seat_project_id(html):
    for match in _GOTO_PATTERN.finditer(html):
        tag_start = html.rfind("<", 0, match.start())
        tag_end = html.find(">", match.end())
        if tag_start < 0 or tag_end < 0:
            continue
        opening = html[tag_start : tag_end + 1]
        if "onclick" not in opening and "href" not in opening:
            continue
        close_start = html.find("</", tag_end)
        close_end = html.find(">", close_start) if close_start >= 0 else -1
        text_end = close_end + 1 if close_end >= 0 else min(len(html), tag_end + 500)
        text = re.sub(r"<[^>]+>", "", html[tag_end + 1 : text_end])
        if "座位预约" in text:
            return match.group(1)
    return ""


def token_from_location(location):
    parsed = urllib.parse.urlsplit(location)
    token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
    if token:
        return token
    if "?" in parsed.fragment:
        fragment_query = parsed.fragment.split("?", 1)[1]
        token = urllib.parse.parse_qs(fragment_query).get("token", [""])[0]
        if token:
            return token
    raise LoginFailed("重定向地址中没有 handoff token")


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _headers(request):
    request.headers["Accept"] = _ACCEPT_HTML
    request.headers["Accept-Language"] = _ACCEPT_LANGUAGE
    request.headers["User-Agent"] = USER_AGENT


def portal_error(exc):
    """Map a failed entry request to a typed error."""
    if exc.code in (403, 503):
        return UpstreamBlocked(
            "座位系统暂时不可用（HTTP %d，可能是夜间关闭或网络限制）" % exc.code
        )
    return LoginFailed("无法打开 CAS 登录页：HTTP %d" % exc.code)


class Authenticator:
    def __init__(self, api=None, timeout=PORTAL_TIMEOUT):
        self._api = api or ApiClient()
        self._timeout = timeout

    def login(self, stu_id, password):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

        entry_url = REM_BASE_URL + "/static/sso/webOAuthRed"
        entry_request = urllib.request.Request(entry_url, method="GET")
        _headers(entry_request)
        try:
            with opener.open(entry_request, timeout=self._timeout) as response:
                final_url = response.geturl()
                page = response.read()
        except urllib.error.HTTPError as exc:
            raise portal_error(exc)
        except urllib.error.URLError as exc:
            raise LoginFailed("无法打开 CAS 登录页：%s" % (exc,))

        if urllib.parse.urlsplit(final_url).hostname != "account.ccnu.edu.cn":
            raise LoginFailed("未跳转到 CAS 登录页：%s" % final_url)

        lt, execution, action = parse_cas_form(page.decode("utf-8", "replace"))
        action_url = urllib.parse.urljoin(final_url, action)

        form = urllib.parse.urlencode(
            {
                "username": stu_id,
                "password": password,
                "lt": lt,
                "execution": execution,
                "_eventId": "submit",
                "submit": "登录",
            }
        ).encode("utf-8")
        login_request = urllib.request.Request(action_url, data=form, method="POST")
        _headers(login_request)
        login_request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        login_request.headers["Origin"] = "https://account.ccnu.edu.cn"
        login_request.headers["Referer"] = action_url
        try:
            with opener.open(login_request, timeout=self._timeout) as response:
                result_url = response.geturl()
                result_page = response.read()
        except urllib.error.URLError as exc:
            raise LoginFailed("提交登录表单失败：%s" % (exc,))

        if urllib.parse.urlsplit(result_url).hostname == "account.ccnu.edu.cn":
            raise InvalidCredentials("学号或密码错误")

        project_id = find_seat_project_id(
            result_page.decode("utf-8", "replace")
        ) or SEAT_RESERVATION_PROJECT_ID

        no_redirect = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar), _NoRedirectHandler()
        )
        goto_request = urllib.request.Request(
            REM_BASE_URL + "/static/gotoProject/" + project_id, method="GET"
        )
        _headers(goto_request)
        try:
            response = no_redirect.open(goto_request, timeout=self._timeout)
        except urllib.error.HTTPError as exc:
            if exc.code != 302:
                raise LoginFailed("打开座位预约项目失败：HTTP %d" % exc.code)
            location = exc.headers.get("Location") or ""
        else:
            response.close()
            raise LoginFailed("打开座位预约项目失败：未返回重定向")

        handoff_token = token_from_location(location)
        exchange_url = (
            JSQ_BASE_URL
            + "/static/public/auth/cas/"
            + urllib.parse.quote(handoff_token, safe="")
        )
        envelope = self._api.post_envelope(
            exchange_url, {"token": handoff_token, "loginType": "PC"}, ""
        )
        data = envelope.get("data") or {}
        session_token = data.get("token") or ""
        if not session_token:
            raise LoginFailed("登录失败：未返回 Session Token")
        return session_token
