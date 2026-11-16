"""Short-lived Session Token cache.

Reuses one CAS login across the commands of a single conversation flow.
The cache is keyed by student ID, written 0600, and expires after five
minutes (the same client-side TTL the Go client uses).
"""

import os
import time

from . import storage

DEFAULT_TTL_SECONDS = 300


def default_cache_path(environ=None):
    env = os.environ if environ is None else environ
    base = env.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "ccnu-seat-reservation", "session.json")


class SessionCache:
    def __init__(self, path=None, ttl=DEFAULT_TTL_SECONDS, environ=None, clock=time.time):
        self.path = path or default_cache_path(environ)
        self.ttl = ttl
        self._clock = clock

    def load(self, stu_id):
        try:
            payload = storage.read_json(self.path)
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("stu_id") != stu_id:
            return None
        token = payload.get("token") or ""
        try:
            expires_at = float(payload.get("expires_at") or 0)
        except (TypeError, ValueError):
            return None
        if not token or expires_at <= self._clock():
            return None
        return token

    def save(self, stu_id, token):
        storage.write_private_json(
            self.path,
            {
                "stu_id": stu_id,
                "token": token,
                "expires_at": self._clock() + self.ttl,
            },
        )

    def clear(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass
