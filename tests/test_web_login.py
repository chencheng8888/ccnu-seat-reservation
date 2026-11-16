import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

from ccnu_reservation.web_login import WebLoginServer, render_form


class RenderFormTest(unittest.TestCase):
    def test_escapes_student_id_and_error(self):
        page = render_form('<script>"x"</script>', "/t", "<b>bad</b>")
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("&lt;b&gt;bad&lt;/b&gt;", page)

    def test_form_posts_to_token_path(self):
        page = render_form("20210001", "/secret-token")
        self.assertIn('action="/secret-token"', page)
        self.assertIn('name="password"', page)


class WebLoginServerTest(unittest.TestCase):
    def _run(self, server, timeout=10):
        result = {}
        thread = threading.Thread(
            target=lambda: result.setdefault("value", server.wait(timeout)),
            daemon=True,
        )
        thread.start()
        return thread, result

    def test_accepts_one_submission(self):
        server = WebLoginServer("20210001")
        self.addCleanup(server.close)
        thread, result = self._run(server)
        data = urllib.parse.urlencode(
            {"stu_id": "20210001", "password": "s3cret"}
        ).encode()
        with urllib.request.urlopen(server.url, data=data, timeout=5) as response:
            self.assertEqual(response.status, 200)
        thread.join(5)
        self.assertEqual(result.get("value"), ("20210001", "s3cret"))

    def test_rejects_unknown_path(self):
        server = WebLoginServer()
        self.addCleanup(server.close)
        thread, _ = self._run(server, timeout=1)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(server.url + "x", timeout=5)
        self.assertEqual(ctx.exception.code, 404)
        thread.join(3)

    def test_timeout_returns_none(self):
        server = WebLoginServer()
        self.addCleanup(server.close)
        self.assertIsNone(server.wait(0.2))


if __name__ == "__main__":
    unittest.main()
