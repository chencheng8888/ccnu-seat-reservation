import unittest

from ccnu_reservation.transport import sign_request


class SignRequestTest(unittest.TestCase):
    # Vector generated independently with:
    # printf 'seat::<uuid>::<ts>::POST' | openssl dgst -sha256 -hmac 'test-key'
    def test_known_vector(self):
        digest = sign_request(
            b"test-key",
            "11111111-2222-4333-8444-555555555555",
            "1700000000000",
            "POST",
        )
        self.assertEqual(
            digest,
            "fbc1edf17654d993ddfce8659c4039275f46ccb5d0b1e4b6a77c9d1e1d640fc3",
        )

    def test_message_shape(self):
        self.assertEqual(
            sign_request(b"k", "rid", "123"),
            sign_request(b"k", "rid", "123", "POST"),
        )


if __name__ == "__main__":
    unittest.main()
