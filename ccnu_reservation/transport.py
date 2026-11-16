"""HTTP transport, HMAC signing and envelope handling."""

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

from . import aes
from .errors import ApiError, NetworkError, ProtocolError, SessionExpired, UpstreamBlocked

JSQ_BASE_URL = "https://kjyy.ccnu.edu.cn/jsq"
REM_BASE_URL = "https://kjyy.ccnu.edu.cn/rem"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 25


def sign_request(key, request_id, timestamp, method="POST"):
    """HMAC-SHA256 hex of ``seat::<uuid>::<ms>::<method>``."""
    message = "seat::%s::%s::%s" % (request_id, timestamp, method)
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def escape_control_chars_in_strings(data):
    """Escape raw control bytes inside JSON string literals.

    The upstream occasionally returns invalid JSON with literal control
    characters (notably in ``likeSeats``). Outside strings the bytes are left
    untouched.
    """
    output = bytearray()
    in_string = False
    escaped = False
    for byte in data:
        if not in_string:
            output.append(byte)
            if byte == 0x22:  # '"'
                in_string = True
            continue
        if escaped:
            output.append(byte)
            escaped = False
            continue
        if byte == 0x5C:  # '\\'
            output.append(byte)
            escaped = True
        elif byte == 0x22:  # '"'
            output.append(byte)
            in_string = False
        elif byte == 0x0A:
            output.extend(b"\\n")
        elif byte == 0x0D:
            output.extend(b"\\r")
        elif byte == 0x09:
            output.extend(b"\\t")
        elif byte < 0x20:
            output.extend(("\\u%04x" % byte).encode("ascii"))
        else:
            output.append(byte)
    return bytes(output)


def decode_envelope(raw):
    """Decode ``{status, code, message, data}`` and raise typed errors."""
    try:
        payload = json.loads(escape_control_chars_in_strings(raw).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError("响应不是合法 JSON：%s" % exc)
    if not isinstance(payload, dict):
        raise ProtocolError("响应不是 JSON 对象")
    if payload.get("status") is not True:
        code = payload.get("code")
        try:
            code = int(code)
        except (TypeError, ValueError):
            code = 0
        message = payload.get("message") or "上游返回失败"
        if code in (20002, 20003):
            raise SessionExpired(message or "Session 已过期")
        raise ApiError(code, message)
    return payload


@dataclass(frozen=True)
class SystemInfo:
    hmac: int
    hmac_key: bytes
    step: int
    max_duration: int
    future_make_day: int


def _truncate(raw, limit=300):
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    return text[:limit] + "..." if len(text) > limit else text


def _set_headers(request, headers):
    # Assign directly so header names keep their upstream casing.
    for name, value in headers.items():
        request.headers[name] = value


class ApiClient:
    def __init__(self, timeout=REQUEST_TIMEOUT):
        self._timeout = timeout
        self._system = None

    def post(self, url, body=None, token=""):
        payload = json.dumps(
            {} if body is None else body, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        request = urllib.request.Request(url, data=payload, method="POST")
        _set_headers(
            request,
            {
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://kjyy.ccnu.edu.cn",
                "Referer": "https://kjyy.ccnu.edu.cn/jsq-v/",
                "User-Agent": USER_AGENT,
                "loginType": "PC",
            },
        )
        if token:
            _set_headers(request, {"token": token})
            info = self.system_info()
            if info.hmac == 1:
                request_id = str(uuid.uuid4())
                timestamp = str(int(time.time() * 1000))
                _set_headers(
                    request,
                    {
                        "X-request-id": request_id,
                        "X-request-date": timestamp,
                        "X-hmac-request-key": sign_request(
                            info.hmac_key, request_id, timestamp, "POST"
                        ),
                    },
                )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 503):
                exc.close()
                raise UpstreamBlocked(
                    "座位系统暂时不可用（HTTP %d，可能是夜间关闭或网络限制）" % exc.code
                )
            body = exc.read()
            raise NetworkError(
                "HTTP %d from %s: %s" % (exc.code, url, _truncate(body))
            )
        except urllib.error.URLError as exc:
            raise NetworkError("请求失败：%s" % (exc.reason,))
        if status != 200:
            raise NetworkError("HTTP %d from %s" % (status, url))
        return raw

    def post_envelope(self, url, body=None, token=""):
        return decode_envelope(self.post(url, body, token))

    def system_info(self):
        if self._system is not None:
            return self._system
        envelope = self.post_envelope(
            JSQ_BASE_URL + "/static/public/cg/getSysSet/PC", None, ""
        )
        data = envelope.get("data") or {}
        hmac_enabled = int(data.get("hmac") or 0)
        key = b""
        if hmac_enabled == 1:
            try:
                key = aes.decrypt_hmac_key(data.get("hmacKey") or "")
            except ValueError as exc:
                raise ProtocolError("无法解密 HMAC key：%s" % exc)
        self._system = SystemInfo(
            hmac=hmac_enabled,
            hmac_key=key,
            step=int(data.get("stepMinute") or 0),
            max_duration=int(data.get("maxMinute") or 0),
            future_make_day=int(data.get("futureMakeDay") or 0),
        )
        return self._system
