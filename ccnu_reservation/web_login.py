"""Browser-based credential entry for environments without a TTY.

``ccnu login --web`` starts a one-shot HTTP server bound to 127.0.0.1, opens a
local page, and hands the submitted credentials straight to the CLI process.
The password never passes through stdout, the conversation, or a command-line
argument. The server accepts exactly one submission, never logs request
bodies, and shuts down when the process exits.
"""

import html
import secrets
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SUCCESS_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>已收到</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
max-width:28rem;margin:15vh auto;padding:0 1.5rem;color:#1f2328;background:#fff}
h1{font-size:1.25rem}p{line-height:1.6;color:#57606a}
</style></head>
<body><h1>已收到凭据</h1>
<p>正在本机验证并保存，结果会显示在终端里。现在可以关闭这个页面。</p>
</body></html>"""


def render_form(stu_id_hint="", action="/", error=""):
    hint = html.escape(stu_id_hint or "", quote=True)
    action_attr = html.escape(action or "/", quote=True)
    error_html = (
        '<p class="error">%s</p>' % html.escape(error, quote=False) if error else ""
    )
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CCNU 图书馆座位预约 · 登录</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
max-width:28rem;margin:12vh auto;padding:0 1.5rem;color:#1f2328;background:#fff}
h1{font-size:1.25rem}label{display:block;margin:1rem 0;color:#57606a;font-size:.9rem}
input{display:block;width:100%%;margin-top:.35rem;padding:.6rem;font-size:1rem;
border:1px solid #d0d7de;border-radius:6px}
button{margin-top:.5rem;padding:.6rem 1.1rem;font-size:1rem;border:0;border-radius:6px;
background:#1f6feb;color:#fff;cursor:pointer}
p{line-height:1.6;color:#57606a}.error{color:#cf222e}
</style></head>
<body>
<h1>登录 CCNU 图书馆</h1>
<p>凭据只保存在本机，不会出现在对话或终端输出里。</p>
%s
<form method="post" action="%s">
  <label>学号
    <input name="stu_id" value="%s" autocomplete="username" required autofocus>
  </label>
  <label>密码
    <input type="password" name="password" autocomplete="off" required>
  </label>
  <button type="submit">登录</button>
</form>
</body></html>""" % (error_html, action_attr, hint)


class WebLoginServer:
    def __init__(self, stu_id_hint="", port=0):
        self.token = secrets.token_urlsafe(24)
        self._captured = {}
        self._stu_id_hint = stu_id_hint
        self.httpd = HTTPServer(("127.0.0.1", port), self._make_handler())

    @property
    def url(self):
        return "http://127.0.0.1:%d/%s" % (self.httpd.server_address[1], self.token)

    def _make_handler(self):
        token = self.token
        captured = self._captured
        hint = self._stu_id_hint

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status, body):
                payload = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                if self.path != "/" + token:
                    self.send_error(404)
                    return
                self._send(200, render_form(hint, "/" + token))

            def do_POST(self):
                if self.path != "/" + token:
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    self.send_error(400)
                    return
                if not 0 < length <= 8192:
                    self.send_error(413)
                    return
                form = urllib.parse.parse_qs(
                    self.rfile.read(length).decode("utf-8", "replace")
                )
                stu_id = (form.get("stu_id") or [""])[0].strip()
                password = (form.get("password") or [""])[0]
                if not stu_id or not password:
                    self._send(
                        200,
                        render_form(hint, "/" + token, "学号和密码不能为空"),
                    )
                    return
                captured["stu_id"] = stu_id
                captured["password"] = password
                self._send(200, SUCCESS_HTML)

            def log_message(self, *args):
                # Request lines and bodies must never reach logs.
                return

        return Handler

    def wait(self, timeout=180):
        deadline = time.monotonic() + timeout
        while not self._captured:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self.httpd.timeout = remaining
            self.httpd.handle_request()
        return (self._captured["stu_id"], self._captured["password"])

    def close(self):
        self.httpd.server_close()


def prompt_credentials(stu_id_hint="", timeout=180, open_browser=True):
    server = WebLoginServer(stu_id_hint)
    try:
        if open_browser:
            webbrowser.open(server.url)
        # stderr keeps stdout clean for --json mode.
        print("登录页：%s" % server.url, file=sys.stderr)
        return server.wait(timeout)
    finally:
        server.close()
