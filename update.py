"""Installer + on-demand updater for PortableSearXNG.

Run via install.bat (--install, fresh install) or update.bat (no args,
on-demand update). Update mode checks two upstreams - the SearXNG source
(github.com/searxng/searxng, master) and this kit's own scripts (latest
GitHub release of KIT_REPO) - shows what is available with review URLs,
and asks which to apply. A SearXNG update replaces the vendored searxng/
tree (with searxng.old/ rollback on failure); a scripts update replaces
the kit's own files (start.bat, update.py, shims, ...) but never the
user's config.ini / settings.yml / limiter.toml, and never update.bat
(a running batch file must not be rewritten - cmd re-reads it by byte
offset; update.bat therefore stays a frozen trampoline and all real
logic lives here, where self-replacement is safe because Python has
already loaded this file).

Flags (mainly for scripting/tests): --all, --searxng-only,
--scripts-only skip the interactive menu; --no-self-update suppresses
the kit check (used internally after a scripts update re-runs this
file for the SearXNG phase).

All network access goes through curl.exe (Windows' built-in curl, which
uses the Windows certificate store) instead of urllib/ssl/certifi. This
gives consistent TLS behaviour (including behind corporate MITM proxies)
and consistent proxy environment-variable handling with install.bat, which
also shells out to curl.exe.
"""

import datetime
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))

# the embeddable Python's ._pth pins sys.path and the kit dir is not on it
sys.path.insert(0, BASE)
import getcfg  # noqa: E402
CURL = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe")

API_URL = "https://api.github.com/repos/searxng/searxng/commits/master"
ZIP_URL = "https://github.com/searxng/searxng/archive/{sha}.zip"
FALLBACK_ZIP_URL = "https://codeload.github.com/searxng/searxng/zip/refs/heads/master"
COMPARE_URL = "https://github.com/searxng/searxng/compare/{old}...{new}"
COMMIT_URL = "https://github.com/searxng/searxng/commit/{sha}"

KIT_REPO = "VraethrDalkr/portable-searxng"  # the public scripts repo (owner/name)
KIT_API_URL = f"https://api.github.com/repos/{KIT_REPO}/releases/latest"

COMMIT_FILE = os.path.join(BASE, "searxng.commit")
VERSION_FILE = os.path.join(BASE, "VERSION")
SRC_DIR = os.path.join(BASE, "searxng")
OLD_DIR = os.path.join(BASE, "searxng.old")
SCRIPTS_OLD_DIR = os.path.join(BASE, "scripts.old")

# files a scripts update must never replace: update.bat is the frozen
# trampoline (see module docstring), config.ini is the user's
KIT_FROZEN = {"update.bat", "config.ini"}
# shipped defaults the user is expected to have edited: the live file is
# never touched, the pristine copy is tracked as <name>.dist instead
KIT_DIST = {"settings.yml", "limiter.toml"}


def curl_get(url: str, dest: str) -> bool:
    """Download url to dest via curl.exe. Returns True on success, False on
    any failure (curl missing, network error, HTTP error, etc.) - callers
    decide how to react rather than getting an exception.
    """
    try:
        subprocess.run(
            [CURL, "-fsSL", "--connect-timeout", "30", "--retry", "3", "--retry-delay", "2", "-o", dest, url],
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def server_running(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def apply_windows_patches(src_dir: str) -> None:
    """Re-apply local Windows fixes that live in the vendored tree.

    searx/webutils.py builds static-file and result-template lists with
    OS-native (backslash) paths, but webapp.py compares them against
    forward-slash strings: assets 404 (unstyled pages) and HTML search
    results 500 with TemplateNotFound. Each patch is skipped silently once
    upstream ships its own fix.
    """
    path = os.path.join(src_dir, "searx", "webutils.py")
    patches = [
        # (name, broken, fixed)
        ("static-path",
         "file_list.append(str(f.relative_to(static_path)))",
         "file_list.append(f.relative_to(static_path).as_posix())"),
        ("result-template-path",
         "f = os.path.join(directory[templates_path_length:], filename)\n",
         "f = os.path.join(directory[templates_path_length:], filename).replace(os.sep, '/')\n"),
    ]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for name, broken, fixed in patches:
        if broken in text:
            text = text.replace(broken, fixed)
            print(f"  applied Windows {name} patch to searx/webutils.py")
        elif fixed not in text:
            print(f"  NOTE: Windows {name} patch location changed upstream - "
                  "if pages break, check searx/webutils.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_version_frozen(src_dir: str, short_id: str, date_iso: str) -> None:
    d = datetime.datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
    version = f"{d.year}.{d.month}.{d.day}+{short_id}"
    with open(os.path.join(src_dir, "searx", "version_frozen.py"), "w", encoding="utf-8") as f:
        f.write(
            f'VERSION_STRING = "{version}"\n'
            f'VERSION_TAG = "{version}"\n'
            f'DOCKER_TAG = "{version.replace("+", "-")}"\n'
            f'GIT_URL = "https://github.com/searxng/searxng"\n'
            f'GIT_BRANCH = "master"\n'
        )


def resolve_latest(tmp: str):
    """Ask the GitHub API what "latest master" is WITHOUT downloading the
    source zip, so an already-up-to-date check costs one small API call
    instead of a ~7 MB archive download.

    Returns (sha, date_iso, subject), or None when the API is unavailable
    (rate limiting - 60 req/h unauthenticated, network quirks, proxies that
    block api.github.com) - the caller then falls back to downloading the
    master branch zip blind.
    """
    api_tmp = os.path.join(tmp, "api_response.json")
    if not curl_get(API_URL, api_tmp):
        return None
    try:
        with open(api_tmp, encoding="utf-8") as f:
            head = json.load(f)
        return head["sha"], head["commit"]["committer"]["date"], head["commit"]["message"].splitlines()[0]
    except (OSError, ValueError, KeyError, IndexError):
        return None


def read_searxng_commit() -> str:
    try:
        with open(COMMIT_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def read_kit_version() -> str:
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def resolve_kit_latest(tmp: str):
    """Latest kit release: (tag, zipball_url, html_url), or None when the
    API is unreachable, rate-limited, or the repo has no release yet.
    Unlike the SearXNG path there is no blind fallback - a scripts update
    is never critical, so on failure the menu just marks it unavailable.
    """
    api_tmp = os.path.join(tmp, "kit_api_response.json")
    if not curl_get(KIT_API_URL, api_tmp):
        return None
    try:
        with open(api_tmp, encoding="utf-8") as f:
            rel = json.load(f)
        return rel["tag_name"], rel["zipball_url"], rel["html_url"]
    except (OSError, ValueError, KeyError):
        return None


def download_source(tmp: str, sha: str | None):
    """Download the source zip for `sha`, or the master branch zip when the
    sha is unknown (API unavailable) or the sha-specific download fails.

    In fallback mode the exact sha is unknown, so the commit pin is recorded
    as "master@<YYYY-MM-DD utc>", a string that never equals a real sha - so
    the next update run naturally re-checks and refreshes instead of getting
    stuck thinking it's up to date forever.

    Returns (tag, short_id, zip_path); tag is the sha when known.
    """
    zip_path = os.path.join(tmp, "searxng.zip")
    if sha is not None:
        print("Downloading new source archive...")
        if curl_get(ZIP_URL.format(sha=sha), zip_path):
            return sha, sha[:7], zip_path
        print("  archive download for that commit failed - falling back to the master branch zip...")

    print("Downloading master branch archive directly...")
    if not curl_get(FALLBACK_ZIP_URL, zip_path):
        raise RuntimeError(
            "could not download SearXNG source from GitHub "
            "(both the API and the direct branch zip failed - check your internet connection)"
        )
    date_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return f"master@{date_iso}", "master", zip_path


def extract_source_zip(zip_path: str, dest_dir: str) -> None:
    """Extract a GitHub source zip into dest_dir, stripping the single
    top-level folder (searxng-<sha>, owner-repo-<sha>, ...) the archive
    wraps everything in.

    Skips utils/templates/ entries (symlinks with no meaning on Windows)
    and, belt-and-braces, any entry whose Unix file mode marks it as a
    symlink regardless of path.
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            raise RuntimeError("downloaded archive is empty")
        top_level = names[0].split("/")[0]
        for info in zf.infolist():
            name = info.filename
            if not name.startswith(top_level + "/"):
                continue
            rel = name[len(top_level) + 1:]
            if not rel:
                continue  # the top-level directory entry itself
            if "/utils/templates/" in name:
                continue
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                continue
            target = os.path.join(dest_dir, rel)
            if name.endswith("/"):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def pip_install_requirements(requirements_path: str) -> None:
    print("Installing/upgrading Python dependencies...")
    try:
        # tzdata is appended because the embeddable Python has no OS timezone
        # database; without it zoneinfo lookups fail and engines that localize
        # timestamps (e.g. bilibili) crash with tracebacks at load time.
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-warn-script-location",
             "--only-binary=:all:", "-r", requirements_path, "tzdata"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "pip install failed - a required package has no prebuilt wheel for this "
            "Python/Windows combination. --only-binary=:all: deliberately forbids "
            "building from source (that would need a full MSVC toolchain and can hang "
            "for a long time). See the pip output above for which package failed."
        ) from exc


def sanity_check(new_src_dir: str) -> None:
    print("Sanity-checking the new tree...")
    subprocess.run(
        [sys.executable, "-c", "import searx, searx.webapp, lxml, msgspec"],
        check=True,
        env={**os.environ, "SEARXNG_SETTINGS_PATH": os.path.join(BASE, "settings.yml")},
    )


def refresh_dist(src: str, name: str) -> None:
    """Track a changed shipped default as <name>.dist without ever touching
    the live, user-edited file.
    """
    dist = os.path.join(BASE, name + ".dist")
    with open(src, "rb") as f:
        new = f.read()
    try:
        with open(dist, "rb") as f:
            old = f.read()
    except OSError:
        old = None
    if new == old:
        return
    with open(dist, "wb") as f:
        f.write(new)
    if old is not None:
        print(f"  NOTE: the shipped default {name} changed - compare {name}.dist "
              f"with your {name} and port over what you want.")


def update_scripts(tag: str, zipball_url: str) -> None:
    """Replace the kit's own files with the given release. The replaced
    versions are kept for one cycle in scripts.old\\. Everything in the
    release lands in the instance except KIT_FROZEN (never replaced) and
    KIT_DIST (tracked as .dist copies) - a denylist, so files added to
    future kit releases arrive without this updater knowing about them.
    """
    print(f"Updating scripts to {tag}...")
    tmp = tempfile.mkdtemp(prefix="psx-scripts-")
    try:
        zip_path = os.path.join(tmp, "kit.zip")
        if not curl_get(zipball_url, zip_path):
            raise RuntimeError("could not download the scripts archive from GitHub")
        new_tree = os.path.join(tmp, "kit-new")
        os.makedirs(new_tree)
        extract_source_zip(zip_path, new_tree)
        if not os.path.isfile(os.path.join(new_tree, "update.py")):
            raise RuntimeError("downloaded archive does not look like a PortableSearXNG kit")

        # a broken update.py must never land - the updater can't self-heal
        py_files = [os.path.join(dp, f)
                    for dp, _, fs in os.walk(new_tree) for f in fs if f.endswith(".py")]
        if py_files:
            print("  syntax-checking the new scripts...")
            subprocess.run([sys.executable, "-m", "py_compile", *py_files], check=True)

        if os.path.isdir(SCRIPTS_OLD_DIR):
            shutil.rmtree(SCRIPTS_OLD_DIR)
        for dirpath, dirnames, filenames in os.walk(new_tree):
            # the syntax check above just created __pycache__ dirs - never
            # copy those into the instance
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for filename in filenames:
                src = os.path.join(dirpath, filename)
                rel = os.path.relpath(src, new_tree)
                if rel in KIT_FROZEN:
                    continue
                if rel in KIT_DIST:
                    refresh_dist(src, rel)
                    continue
                dest = os.path.join(BASE, rel)
                if os.path.exists(dest):
                    backup = os.path.join(SCRIPTS_OLD_DIR, rel)
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.copy2(dest, backup)
                else:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copyfile(src, dest)
                print(f"  updated {rel}")

        # the release's VERSION file should match the tag, but the tag is
        # what the up-to-date check compares against - make sure it wins
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(tag + "\n")

        # shims live in site-packages (install.bat put them there); pip and
        # SearXNG updates never touch them, so re-copy after a scripts update
        shims_dir = os.path.join(BASE, "shims")
        site_packages = os.path.join(BASE, "python", "Lib", "site-packages")
        if os.path.isdir(shims_dir) and os.path.isdir(site_packages):
            for name in os.listdir(shims_dir):
                shutil.copyfile(os.path.join(shims_dir, name),
                                os.path.join(site_packages, name))

        print(f"Scripts updated to {tag} (previous versions kept in scripts.old).")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def update_searxng(install_mode: bool) -> int:
    current = read_searxng_commit()

    print("Checking upstream (github.com/searxng/searxng, branch master)...")
    tmp = tempfile.mkdtemp(prefix="psx-update-")
    try:
        meta = resolve_latest(tmp)
        if meta is not None:
            sha, date_iso, subject = meta
            print(f"  installed: {current[:12] or '(none)'}")
            print(f"  latest:    {sha[:12]}  ({date_iso}: {subject})")
            if not install_mode and sha == current:
                print("Already up to date - nothing to do.")
                return 0
            tag, short_id, zip_path = download_source(tmp, sha)
            if tag != sha:
                # sha-specific download failed; the branch zip we got may be
                # newer than the sha the API reported - stamp it with today.
                date_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        else:
            print("  GitHub API call failed (rate limit or network) - falling back to the master branch zip...")
            tag, short_id, zip_path = download_source(tmp, None)
            date_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            print(f"  installed: {current[:12] or '(none)'}")
            print(f"  latest:    {tag}  (fetched via direct branch zip, exact sha unknown)")
            if not install_mode and tag == current:
                print("Already up to date (fallback pin matches today) - nothing to do.")
                return 0

        print("Extracting...")
        new_tree = os.path.join(tmp, "searxng-new")
        os.makedirs(new_tree, exist_ok=True)
        extract_source_zip(zip_path, new_tree)
        if not os.path.isdir(os.path.join(new_tree, "searx")):
            raise RuntimeError("downloaded archive does not look like a SearXNG source tree")
        write_version_frozen(new_tree, short_id, date_iso)
        apply_windows_patches(new_tree)

        requirements_dest = os.path.join(BASE, "requirements.txt")

        if install_mode and not os.path.isdir(SRC_DIR):
            # Fresh install: no previous tree to protect, nothing to roll back to.
            shutil.move(new_tree, SRC_DIR)
            shutil.copyfile(os.path.join(SRC_DIR, "requirements.txt"), requirements_dest)
            pip_install_requirements(requirements_dest)
            sanity_check(SRC_DIR)
        else:
            # Update mode (or an --install re-run where searxng/ exists but
            # searxng.commit is missing, e.g. an interrupted install): keep
            # the old tree until the new one proves itself.
            if os.path.isdir(OLD_DIR):
                shutil.rmtree(OLD_DIR)
            if os.path.isdir(SRC_DIR):
                os.rename(SRC_DIR, OLD_DIR)
            try:
                shutil.move(new_tree, SRC_DIR)
                shutil.copyfile(os.path.join(SRC_DIR, "requirements.txt"), requirements_dest)
                pip_install_requirements(requirements_dest)
                sanity_check(SRC_DIR)
            except Exception:
                print("Update FAILED - rolling back to the previous version...")
                if os.path.isdir(SRC_DIR):
                    shutil.rmtree(SRC_DIR)
                if os.path.isdir(OLD_DIR):
                    os.rename(OLD_DIR, SRC_DIR)
                raise
            if os.path.isdir(OLD_DIR):
                shutil.rmtree(OLD_DIR, ignore_errors=True)

        with open(COMMIT_FILE, "w", encoding="utf-8") as f:
            f.write(tag + "\n")
        verb = "Install" if install_mode else "Update"
        print(f"{verb} complete: now at {tag[:12]}. Start it with start.bat.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def looks_like_sha(s: str) -> bool:
    return len(s) == 40 and all(c in "0123456789abcdef" for c in s.lower())


def main() -> int:
    args = sys.argv[1:]
    install_mode = "--install" in args
    no_self_update = "--no-self-update" in args
    forced = None
    if "--all" in args:
        forced = "both"
    if "--searxng-only" in args:
        forced = "searxng"
    if "--scripts-only" in args:
        forced = "scripts"

    if install_mode:
        # Fresh install: the kit the user just extracted IS the latest
        # scripts, so only SearXNG needs fetching - no menu, no kit check.
        if os.path.isdir(SRC_DIR) and os.path.exists(COMMIT_FILE):
            print("SearXNG already installed.")
            return 0
        return update_searxng(install_mode=True)

    port = int(getcfg.get("port"))
    if server_running(port):
        print(f"SearXNG is still running on port {port}.")
        print("Run stop.bat first, then run update.bat again.")
        return 1

    # --- what is available? ---
    print("Checking for updates...")
    tmp = tempfile.mkdtemp(prefix="psx-check-")
    try:
        sx_meta = resolve_latest(tmp)
        kit_meta = None if no_self_update else resolve_kit_latest(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    sx_current = read_searxng_commit()
    kit_current = read_kit_version()
    sx_uptodate = sx_meta is not None and sx_meta[0] == sx_current
    kit_new = kit_meta is not None and kit_meta[0] != kit_current

    print()
    if sx_meta is None:
        print("SearXNG:  update check failed (GitHub API unreachable or rate-limited)")
        print("          selecting it will fetch the latest master zip anyway")
    elif sx_uptodate:
        print(f"SearXNG:  {sx_current[:12]} - already up to date")
    else:
        sha, date_iso, subject = sx_meta
        print(f"SearXNG:  {sx_current[:12] or '(none)'} -> {sha[:12]}  ({date_iso}: {subject})")
        if looks_like_sha(sx_current):
            print(f"          review: {COMPARE_URL.format(old=sx_current[:12], new=sha[:12])}")
        else:
            print(f"          review: {COMMIT_URL.format(sha=sha[:12])}")
    if not no_self_update:
        if kit_meta is None:
            print("Scripts:  update check failed (offline, rate-limited, or no release yet)")
            print("          scripts update unavailable this run")
        elif not kit_new:
            print(f"Scripts:  {kit_current} - already up to date")
        else:
            print(f"Scripts:  {kit_current or '(unknown)'} -> {kit_meta[0]}")
            print(f"          review: {kit_meta[2]}")

    can_searxng = not sx_uptodate  # includes the API-failed blind path
    if not can_searxng and not kit_new:
        print()
        print("Everything is up to date - nothing to do.")
        return 0

    # --- what does the user want? ---
    if forced is not None:
        choice = forced
    else:
        print()
        print("Update  [1] both   [2] SearXNG only   [3] scripts only   [4] cancel")
        try:
            answer = input("Choice [1]: ").strip()
        except EOFError:
            answer = "4"
        choice = {"": "both", "1": "both", "2": "searxng",
                  "3": "scripts", "4": "cancel"}.get(answer, "cancel")
        if choice == "cancel":
            print("Cancelled - nothing changed.")
            return 0

    # --- scripts phase first, then re-run this file so the SearXNG phase
    # --- always executes the freshly updated logic
    if choice in ("both", "scripts"):
        if not kit_new:
            print("Scripts: nothing to update.")
        else:
            update_scripts(kit_meta[0], kit_meta[1])
            if choice == "both" and can_searxng:
                print()
                print("Re-running the updater (new scripts) for the SearXNG part...")
                return subprocess.run(
                    [sys.executable, os.path.join(BASE, "update.py"),
                     "--searxng-only", "--no-self-update"],
                ).returncode
            return 0

    if choice in ("both", "searxng"):
        if not can_searxng:
            print("SearXNG: nothing to update.")
            return 0
        return update_searxng(install_mode=False)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # surface a readable error instead of a bare traceback
        print(f"[ERROR] {exc.__class__.__name__}: {exc}")
        sys.exit(1)
