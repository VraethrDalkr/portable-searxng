"""PortableSearXNG: log redirection for console-less runs.

start.bat launches the server with pythonw.exe so no terminal window stays
open. Under pythonw, sys.stdout/sys.stderr are None, which would crash or
silently swallow all SearXNG logging - so when (and only when) they are
None, they are redirected. Where to depends on config.ini's "logging"
key: data\\logs\\searxng.log when true, the null device when false (the
default - searches are GET requests, so the log would contain the user's
query history). Console runs (python.exe) are untouched. Lives in
site-packages so update.bat cannot remove it.
"""

import sys


def _redirect_console_less_output():
    if sys.stderr is not None and sys.stdout is not None:
        return
    import io
    import os

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # ask getcfg (single source of truth for config.ini) whether to log;
    # loaded by file path because the instance root is not on sys.path,
    # and via importlib so it never lands there either. On any problem
    # the answer is "no logging" - same as the shipped default.
    enabled = False
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("psx_getcfg", os.path.join(base, "getcfg.py"))
        getcfg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(getcfg)
        enabled = getcfg.get("logging") == "true"
    except Exception:
        pass

    try:
        if enabled:
            log_dir = os.path.join(base, "data", "logs")
            os.makedirs(log_dir, exist_ok=True)
            # line-buffered so the log is readable while the server runs
            stream = io.open(
                os.path.join(log_dir, "searxng.log"), "a", buffering=1, encoding="utf-8", errors="replace"
            )
        else:
            stream = io.open(os.devnull, "w", encoding="utf-8", errors="replace")
    except OSError:
        return
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


_redirect_console_less_output()
del _redirect_console_less_output
