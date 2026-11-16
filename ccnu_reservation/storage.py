"""Private JSON storage: 0600 files inside 0700 directories."""

import json
import os


def ensure_private_dir(directory):
    os.makedirs(directory, mode=0o700, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass


def write_private_json(path, payload):
    directory = os.path.dirname(path)
    if directory:
        ensure_private_dir(directory)
    temp_path = path + ".tmp"
    descriptor = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
