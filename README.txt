PortableSearXNG
================

Project page and latest version:
    https://github.com/VraethrDalkr/portable-searxng

What this is
------------
A private, local metasearch engine (SearXNG) that runs entirely on your
own PC. It queries several search engines on your behalf and shows you
combined results without tracking you or building a profile. Everything
lives in one folder - there is no system-wide installation, no admin
rights needed, and nothing is written outside this folder.


Quick start
-----------
1. IMPORTANT: if you downloaded this as a ZIP file, right-click it,
   choose Properties, and check the "Unblock" box BEFORE extracting.
   This avoids Windows SmartScreen warnings when you run the .bat files
   later. (Not needed if you copied the folder to a FAT32/exFAT USB
   drive - Windows doesn't mark files from those as "downloaded".)

2. Extract this folder anywhere you like - your hard drive, a USB
   stick, anywhere. The path can have spaces and parentheses in it.

3. Run install.bat. This needs an internet connection the first time -
   it fetches a portable Python runtime, SearXNG itself, and its
   dependencies (roughly 120 MB total, from python.org, pypi.org, and
   github.com). If it fails partway (usually a network hiccup), just
   run install.bat again - it picks up where it left off.

4. When installation finishes, your browser opens automatically once
   the server is ready.


Daily use
---------
- start.bat   - starts the server (if not already running) and opens
                your browser to it.
- stop.bat    - stops the server.
- update.bat  - checks for updates to SearXNG itself AND to these
                scripts, shows what's available (with links to review
                the changes), and asks what to update. Stop the server
                first if it's running.

After install, this folder is fully portable: you can move it, rename
its parent folders, copy it to another PC, or run it from a USB stick.
Everything it needs is inside the folder.


Settings (config.ini)
---------------------
Edit config.ini with any text editor. It has three settings:

    port = 8080

The port the local server listens on. Changing it is mainly useful if
you want to run two instances at once (copy the whole folder and give
the copy a different port).

    browser = ..\FirefoxPortable\FirefoxPortable.exe

Optional: which browser start.bat opens the search page in. Leave it
empty to use your Windows default browser. You can give a full path
(C:\Program Files\Mozilla Firefox\firefox.exe) or a path relative to
this folder - handy for a portable browser that travels on the same
USB stick, like the example above. If the path doesn't exist you get
a warning and the default browser is used instead.

    open_browser = yes

Whether start.bat opens the search page in a browser once the server
is ready. Set it to no to only start the server.


Starting SearXNG with Windows
-----------------------------
To have SearXNG always running in the background without a search
page popping up on every boot:

1. Set open_browser = no in config.ini.
2. Press Win+R, type shell:startup and press Enter.
3. Right-click-drag start.bat into the folder that opened and choose
   "Create shortcuts here".

The server then starts (briefly showing a console window) whenever you
log in, and searching is always one bookmark away.


Updating
--------
Run update.bat. It checks two things separately and lets you pick:

- SearXNG itself (the search engine code, from its official repo)
- these scripts (start.bat, update.py, etc., from this kit's repo)

A scripts update never touches your config.ini or settings.yml. The
files settings.yml.dist and limiter.toml.dist are pristine copies of
the shipped defaults: when an update changes the defaults, the .dist
file is refreshed and you're told, so you can compare it against your
(possibly edited) live file and copy over what you want. The replaced
script files are kept one round in scripts.old\ just in case.


Preferences
------------
Personal preferences (theme, default engines, results per page, etc.)
are set from the web UI (the gear/settings icon) and are stored in your
browser, not in this folder. If you want your preferences to follow you
across computers, use a portable web browser stored alongside this
folder, or export/import the preferences URL that the settings page
generates.

Instance-wide defaults (things every visitor gets by default) are
configured by editing settings.yml directly.


Engine setup (what's on / off, and why)
-----------------------------------------
The default engine selection is tuned for privacy and result quality:

- Independent, privacy-respecting indexes are enabled: Mojeek, Brave,
  Qwant, Mwmbl.
- Private frontends to bigger engines are enabled: DuckDuckGo,
  Startpage.
- Google (CSE), Bing, and Yandex are disabled by default - they are
  available on demand via their "bang" shortcuts only. Type the bang in
  the search box to use that engine just for that one query:
      !goc  your search   - Google (via Custom Search)
      !goci your search   - Google image search
      !bi   your search   - Bing
      !yd   your search   - Yandex
  This keeps them out of the default fan-out (no traffic goes to them
  unless you explicitly ask) while keeping the capability one bang away.
- Ranking weights are intentionally flat (equal) across engines so that
  results are decided by consensus across engines, not by a manual
  thumb on the scale. Please don't "fix" this by reweighting engines -
  it's flat on purpose. The one exception is Mwmbl, which is muted
  slightly (weight 0.6) because its crowdsourced index is thin and
  noisy enough to flood page one if left at full weight.
- Marginalia is present but disabled by default - it requires a free
  API key. To enable it: email contact@marginalia-search.com to
  request a key, then in settings.yml set marginalia's "disabled" to
  false and add your key as "api_key".


Credits
-------
- SearXNG (https://github.com/searxng/searxng) - the actual metasearch
  engine doing all the real work, AGPL-3.0. This kit only makes it
  portable on Windows.
- DysDaemoN - first beta tester, and the original idea that this
  should be a proper portable app in the first place.

License: this kit is free software under the GNU AGPL-3.0 (see the
LICENSE file) - the same license as SearXNG itself.


Caveats
-------
- This is for local/personal use: it binds to 127.0.0.1 (localhost)
  only and has no multi-user accounts - anyone with access to this PC
  and this port can use it, but it is not reachable from the network or
  the internet.
- Brave and Mojeek may briefly rate-limit you if you fire off a lot of
  searches in a short burst. This is normal and clears up on its own
  after a short wait.
- The first time you start it, Windows Firewall may pop up asking to
  allow the Python process to communicate. It only needs loopback
  (127.0.0.1) access, so choosing "deny" (or just closing the prompt)
  is safe and the server will still work locally.
