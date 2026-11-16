import json
import os
import stat
import tempfile
import unittest

from ccnu_reservation import config
from ccnu_reservation.errors import NotConfigured


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "ccnu-seat-reservation", "config.json")

    def test_save_then_load(self):
        config.save_credentials("20210001", "s3cret", path=self.path)
        creds = config.load_credentials(path=self.path, environ={})
        self.assertEqual(creds.stu_id, "20210001")
        self.assertEqual(creds.password, "s3cret")
        self.assertEqual(creds.source, "file")

    def test_config_file_is_private(self):
        config.save_credentials("20210001", "s3cret", path=self.path)
        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(mode, 0o600)

    def test_environment_overrides_file(self):
        config.save_credentials("20210001", "file-password", path=self.path)
        creds = config.load_credentials(
            path=self.path,
            environ={"CCNU_STUID": "env-id", "CCNU_PASSWORD": "env-password"},
        )
        self.assertEqual(creds.stu_id, "env-id")
        self.assertEqual(creds.password, "env-password")
        self.assertEqual(creds.source, "env")

    def test_missing_file_raises_not_configured(self):
        with self.assertRaises(NotConfigured):
            config.load_credentials(path=self.path, environ={})

    def test_corrupt_file_raises_not_configured(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as handle:
            handle.write(json.dumps({"stu_id": "only-id"}))
        with self.assertRaises(NotConfigured):
            config.load_credentials(path=self.path, environ={})

    def test_mask_student_id(self):
        self.assertEqual(config.mask_student_id("20210001"), "2021****01")
        self.assertEqual(config.mask_student_id("123"), "1**")


if __name__ == "__main__":
    unittest.main()
