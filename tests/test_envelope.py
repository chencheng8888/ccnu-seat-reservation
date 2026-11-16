import unittest

from ccnu_reservation.errors import ApiError, SessionExpired
from ccnu_reservation.transport import decode_envelope


class DecodeEnvelopeTest(unittest.TestCase):
    def test_returns_successful_envelope(self):
        env = decode_envelope(b'{"status":true,"code":200,"message":"","data":{"x":1}}')
        self.assertTrue(env["status"])
        self.assertEqual(env["data"], {"x": 1})

    def test_raises_session_expired_for_20002_and_20003(self):
        for code in (20002, 20003):
            raw = ('{"status":false,"code":%d,"message":"expired","data":null}' % code).encode()
            with self.assertRaises(SessionExpired):
                decode_envelope(raw)

    def test_raises_api_error_for_other_failures(self):
        raw = b'{"status":false,"code":40010,"message":"no seat","data":null}'
        with self.assertRaises(ApiError) as ctx:
            decode_envelope(raw)
        self.assertEqual(ctx.exception.code, 40010)
        self.assertIn("no seat", ctx.exception.message)

    def test_tolerates_control_characters_inside_strings(self):
        raw = b'{"status":true,"code":200,"message":"a\nb","data":null}'
        self.assertEqual(decode_envelope(raw)["message"], "a\nb")


if __name__ == "__main__":
    unittest.main()
