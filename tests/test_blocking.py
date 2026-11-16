import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

from ccnu_reservation.auth import portal_error
from ccnu_reservation.errors import UpstreamBlocked
from ccnu_reservation.transport import ApiClient


class _BlockHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = b"blocked"
        self.send_response(403)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


class UpstreamBlockedTest(unittest.TestCase):
    def test_403_from_api_becomes_upstream_blocked(self):
        server = HTTPServer(("127.0.0.1", 0), _BlockHandler)
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        try:
            url = "http://127.0.0.1:%d/static" % server.server_address[1]
            with self.assertRaises(UpstreamBlocked):
                ApiClient(timeout=5).post(url, {})
        finally:
            thread.join(3)
            server.server_close()

    def test_portal_error_maps_status(self):
        blocked = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)
        other = urllib.error.HTTPError("https://x", 500, "Server Error", {}, None)
        self.assertIsInstance(portal_error(blocked), UpstreamBlocked)
        self.assertNotIsInstance(portal_error(other), UpstreamBlocked)


if __name__ == "__main__":
    unittest.main()
