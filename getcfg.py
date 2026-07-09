"""Tiny config.ini reader for the batch scripts and update.py.

Usage: python getcfg.py <key>

Reads config.ini sitting next to this script and prints the value for
<key>. The format is plain "key = value" lines; lines starting with ";"
or "#" are comments. Never fails: any problem (missing file, missing
key, junk value) just prints the built-in default, so batch callers
never have to handle an error case.

Known keys:
  port          - TCP port the server listens on (default 8080)
  browser       - optional browser to open search pages in; a relative
                  path is resolved against this folder and printed
                  absolute; prints nothing when unset
  open_browser  - whether start.bat opens the browser at all; printed
                  normalized to exactly "true" or "false" (default
                  true; no/false/0/off all count as false)
  logging       - whether the server writes its output to
                  data\\logs\\searxng.log; printed normalized to exactly
                  "true" or "false" (default false - the log contains
                  the search queries; yes/true/1/on all count as true)
"""

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = {"port": "8080", "browser": "", "open_browser": "true", "logging": "false"}


def _parse(path: str) -> dict:
    # utf-8-sig: tolerate the BOM Notepad likes to prepend
    cfg = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in ";#[":
                continue
            key, sep, value = line.partition("=")
            if not sep:
                continue
            cfg[key.strip().lower()] = value.strip().strip('"').strip("'")
    return cfg


def get(key: str) -> str:
    default = DEFAULTS.get(key, "")
    try:
        value = _parse(os.path.join(BASE, "config.ini")).get(key, default)
    except Exception:
        return default
    if key == "port" and not value.isdigit():
        return default
    if key == "browser" and value and not os.path.isabs(value):
        value = os.path.normpath(os.path.join(BASE, value))
    if key == "open_browser":
        return "false" if value.lower() in ("no", "false", "0", "off") else "true"
    if key == "logging":
        return "true" if value.lower() in ("yes", "true", "1", "on") else "false"
    return value


if __name__ == "__main__":
    print(get(sys.argv[1] if len(sys.argv) > 1 else "port"))
    sys.exit(0)
