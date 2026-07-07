"""PortableSearXNG: log redirection for console-less runs.

start.bat launches the server with pythonw.exe so no terminal window stays
open. Under pythonw, sys.stdout/sys.stderr are None, which would silently
swallow all SearXNG logging - so when (and only when) they are None, send
them to data\\logs\\searxng.log instead. Console runs (python.exe) are
untouched. Lives in site-packages so update.bat cannot remove it.
"""

import sys


def _redirect_console_less_output():
    if sys.stderr is not None and sys.stdout is not None:
        return
    import io
    import os

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    log_dir = os.path.join(base, "data", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        # line-buffered so the log is readable while the server runs
        stream = io.open(
            os.path.join(log_dir, "searxng.log"), "a", buffering=1, encoding="utf-8", errors="replace"
        )
    except OSError:
        return
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


_redirect_console_less_output()
del _redirect_console_less_output
