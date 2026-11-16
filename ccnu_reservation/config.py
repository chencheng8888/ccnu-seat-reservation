"""Credential storage.

Credentials live at ``$XDG_CONFIG_HOME/ccnu-seat-reservation/config.json``
(default ``~/.config/...``) with mode 0600. Environment variables
``CCNU_STUID`` / ``CCNU_PASSWORD`` take precedence and keep the password off
disk for CI or one-off runs.
"""

import os
from dataclasses import dataclass

from . import storage
from .errors import NotConfigured

CONFIG_DIR_NAME = "ccnu-seat-reservation"
CONFIG_FILE_NAME = "config.json"


@dataclass(frozen=True)
class Credentials:
    stu_id: str
    password: str
    source: str


def _environ(environ):
    return os.environ if environ is None else environ


def default_config_path(environ=None):
    env = _environ(environ)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, CONFIG_DIR_NAME, CONFIG_FILE_NAME)


def mask_student_id(stu_id):
    if len(stu_id) <= 4:
        return stu_id[:1] + "**"
    return stu_id[:4] + "****" + stu_id[-2:]


def load_credentials(path=None, environ=None):
    env = _environ(environ)
    if env.get("CCNU_STUID") and env.get("CCNU_PASSWORD"):
        return Credentials(env["CCNU_STUID"], env["CCNU_PASSWORD"], "env")

    config_path = path or default_config_path(env)
    try:
        payload = storage.read_json(config_path)
        stu_id = payload["stu_id"]
        password = payload["password"]
    except FileNotFoundError:
        raise NotConfigured("尚未配置凭据，请运行 ccnu login")
    except (OSError, ValueError, KeyError, TypeError):
        raise NotConfigured("凭据文件无法读取，请重新运行 ccnu login")
    if not stu_id or not password:
        raise NotConfigured("凭据文件不完整，请重新运行 ccnu login")
    return Credentials(str(stu_id), str(password), "file")


def save_credentials(stu_id, password, path=None):
    config_path = path or default_config_path()
    storage.write_private_json(
        config_path, {"stu_id": stu_id, "password": password}
    )
    return config_path
