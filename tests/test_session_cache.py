import os
import stat
import tempfile
import unittest

from ccnu_reservation.config import Credentials
from ccnu_reservation.session_cache import SessionCache
from ccnu_reservation.client import Session


class _FakeAuthenticator:
    def __init__(self):
        self.calls = 0

    def login(self, stu_id, password):
        self.calls += 1
        return "token-%d" % self.calls


class SessionCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "cache", "session.json")
        self.now = 1000.0

    def _cache(self, ttl=300):
        return SessionCache(path=self.path, ttl=ttl, clock=lambda: self.now)

    def test_save_then_load(self):
        cache = self._cache()
        cache.save("20210001", "abc")
        self.assertEqual(cache.load("20210001"), "abc")

    def test_expired_token_is_ignored(self):
        cache = self._cache(ttl=10)
        cache.save("20210001", "abc")
        self.now += 11
        self.assertIsNone(cache.load("20210001"))

    def test_other_student_does_not_use_cache(self):
        cache = self._cache()
        cache.save("20210001", "abc")
        self.assertIsNone(cache.load("20210002"))

    def test_clear_removes_token(self):
        cache = self._cache()
        cache.save("20210001", "abc")
        cache.clear()
        self.assertIsNone(cache.load("20210001"))

    def test_corrupt_file_is_ignored(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as handle:
            handle.write("not json")
        self.assertIsNone(self._cache().load("20210001"))

    def test_cache_file_is_private(self):
        self._cache().save("20210001", "abc")
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "session.json")

    def _session(self, cache, authenticator):
        return Session(
            lambda: Credentials("20210001", "pw", "file"), authenticator, cache
        )

    def test_reuses_token_across_processes(self):
        authenticator = _FakeAuthenticator()
        cache = SessionCache(path=self.path, clock=lambda: 1000.0)
        first = self._session(cache, authenticator).token()
        second = self._session(cache, authenticator).token()
        self.assertEqual(first, second)
        self.assertEqual(authenticator.calls, 1)

    def test_invalidate_forces_a_new_login(self):
        authenticator = _FakeAuthenticator()
        cache = SessionCache(path=self.path, clock=lambda: 1000.0)
        session = self._session(cache, authenticator)
        self.assertEqual(session.token(), "token-1")
        session.invalidate()
        self.assertEqual(session.token(), "token-2")
        self.assertEqual(authenticator.calls, 2)


if __name__ == "__main__":
    unittest.main()
