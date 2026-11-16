import unittest

from ccnu_reservation import aes


class AesBlockVectorTest(unittest.TestCase):
    def test_encrypt_nist_ecb_vector(self):
        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        plaintext = bytes.fromhex("00112233445566778899aabbccddeeff")
        expected = "69c4e0d86a7b0430d8cdb78070b4c55a"
        self.assertEqual(aes.encrypt_block(plaintext, key).hex(), expected)

    def test_decrypt_nist_ecb_vector(self):
        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        ciphertext = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
        expected = bytes.fromhex("00112233445566778899aabbccddeeff")
        self.assertEqual(aes.decrypt_block(ciphertext, key), expected)


class AesCbcVectorTest(unittest.TestCase):
    def test_decrypt_nist_cbc_vector(self):
        key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
        iv = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        ciphertext = bytes.fromhex(
            "7649abac8119b246cee98e9b12e9197d"
            "5086cb9b507219ee95db113a917678b2"
            "73bed6b8e3c1743b7116e69e22229516"
            "3ff1caa1681fac09120eca307586e1a7"
        )
        expected = bytes.fromhex(
            "6bc1bee22e409f96e93d7e117393172a"
            "ae2d8a571e03ac9c9eb76fac45af8e51"
            "30c81c46a35ce411e5fbc1191a0a52ef"
            "f69f2445df4f9b17ad2b417be66c3710"
        )
        self.assertEqual(aes.cbc_decrypt_raw(ciphertext, key, iv), expected)


class HmacKeyDecryptTest(unittest.TestCase):
    # Vector generated independently with:
    # printf '0123456789abcdef' | openssl enc -aes-128-cbc \
    #   -K 7365727665725f646174655f74696d65 -iv 636c69656e745f646174655f74696d65 -base64
    def test_decrypts_known_openssl_vector(self):
        encoded = "HoJxq8dtg12VgtMSAzB/4S2dBC4ufkwkv0e8WYvf8ao="
        self.assertEqual(aes.decrypt_hmac_key(encoded), b"0123456789abcdef")

    def test_rejects_invalid_base64(self):
        with self.assertRaises(ValueError):
            aes.decrypt_hmac_key("not base64!!")


class Pkcs7Test(unittest.TestCase):
    def test_unpads_full_and_partial_blocks(self):
        self.assertEqual(aes.pkcs7_unpad(b"abc" + bytes([13]) * 13), b"abc")
        self.assertEqual(aes.pkcs7_unpad(bytes([16]) * 16), b"")

    def test_rejects_bad_padding(self):
        bad_cases = (
            b"",  # empty
            b"abc" + bytes([0]),  # zero padding length
            b"abc" + bytes([4, 4, 4]),  # padding bytes disagree
            b"ab" + bytes([5, 5]),  # padding longer than the data
        )
        for bad in bad_cases:
            with self.assertRaises(ValueError):
                aes.pkcs7_unpad(bad)


if __name__ == "__main__":
    unittest.main()
