"""Minimal Windows shim for the Unix-only ``pwd`` module.

SearXNG's ``searx/valkeydb.py`` does ``import pwd`` at module level, which
crashes on Windows even though the module is only used in an error path that
requires a configured valkey/redis URL (PortableSearXNG has none). This stub
satisfies the import; it lives in site-packages so SearXNG source updates
(update.bat) cannot remove it.
"""

from collections import namedtuple
import getpass

struct_passwd = namedtuple(
    "struct_passwd",
    ["pw_name", "pw_passwd", "pw_uid", "pw_gid", "pw_gecos", "pw_dir", "pw_shell"],
)


def _entry(uid=0):
    import os

    return struct_passwd(getpass.getuser(), "x", uid, uid, "", os.path.expanduser("~"), "")


def getpwuid(uid):
    return _entry(uid)


def getpwnam(name):
    return _entry()


def getpwall():
    return [_entry()]
