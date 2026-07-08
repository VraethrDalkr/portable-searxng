# PortableSearXNG

[![Latest release](https://img.shields.io/github/v/release/VraethrDalkr/portable-searxng)](../../releases/latest)
[![License: AGPL-3.0](https://img.shields.io/github/license/VraethrDalkr/portable-searxng)](LICENSE)

A fully portable [SearXNG](https://github.com/searxng/searxng) metasearch
instance for Windows - no admin rights, no system installation, no Docker
or WSL. Everything lives in one folder that you can move, rename, copy to
another PC, or run from a USB stick.

It queries several search engines on your behalf and shows combined
results without tracking you or building a profile.

![Search results in PortableSearXNG running locally on Windows](https://raw.githubusercontent.com/VraethrDalkr/portable-searxng/assets/screenshot.png)

## Requirements

- Windows 10 1803 or newer (needs the built-in `curl.exe` / `tar.exe`)
- An internet connection for the first install (~120 MB: portable Python
  from python.org, SearXNG from GitHub, dependencies from PyPI)

## Quick start (no git needed)

1. **Download:** go to the [latest release](../../releases/latest) and
   under **Assets** download `PortableSearXNG-Setup.zip`.
   (The auto-generated "Source code" zip there works too - it's the
   same scripts - as does the green **Code → Download ZIP** button on
   the repo page. If you *do* use git: `git clone` this repo and later
   `git pull`, but you never need git - `update.bat` keeps installed
   instances current by itself.)
2. **Important:** right-click the downloaded ZIP → Properties → check
   **Unblock** → OK, *before* extracting. This avoids SmartScreen
   warnings when running the .bat files.
3. Extract the folder anywhere - spaces and parentheses in the path are
   fine.
4. Run `install.bat` and wait. When it finishes, your browser opens on
   your own private search page.

**Already have an instance?** Don't extract a new ZIP over it - that
would overwrite your settings. Just run `update.bat`; it updates both
SearXNG and these scripts in place. Your settings always survive:
config.ini is rebuilt from the newest template so you receive new
options automatically, with every value you set kept exactly as you
wrote it. (Only instances older than v0.1.0 need a one-time fresh
start: delete the folder and reinstall.)

## Daily use

| Script       | What it does                                                        |
|--------------|---------------------------------------------------------------------|
| `start.bat`  | Starts the server (if needed) and opens your browser to it          |
| `stop.bat`   | Stops the server                                                    |
| `update.bat` | Checks for updates to SearXNG *and* to these scripts, shows what's available with links to review, and asks what to update |

## Settings

Edit `config.ini` with any text editor:

```ini
; Port the local server listens on.
port = 8080

; Optional: browser to open search pages in.
; Full path, or relative to this folder.
; Leave empty to use the Windows default browser.
;   browser = ..\FirefoxPortable\FirefoxPortable.exe
browser =

; Open the browser when start.bat runs? Set to false if you only want
; the server started - e.g. when start.bat is in your Windows startup
; apps and you don't want a search page popping up on every boot.
; (true/false; yes/no also accepted)
open_browser = true
```

The `browser` setting is handy for a portable browser that travels on
the same USB stick, and `open_browser = false` lets you put `start.bat`
in your Windows startup apps (press `Win+R`, type `shell:startup`) so
the server is always running without a search page opening on every
boot.
Personal search preferences (theme, engines per query, etc.) are set
in the web UI and live in your browser's cookies; instance-wide
defaults live in `settings.yml`.

See `README.txt` inside the kit for the full details: engine selection
rationale, bang shortcuts for the disabled big engines (`!goc`, `!bi`,
`!yd`), how updates treat your edited files, and known caveats.

## Privacy defaults

- Binds to `127.0.0.1` only - not reachable from the network.
- Independent/privacy-respecting engines enabled (Mojeek, Brave, Qwant,
  Mwmbl, DuckDuckGo, Startpage, Wikipedia/Wikidata).
- Google (CSE), Bing, and Yandex are disabled by default and only run
  when you explicitly ask via their bang shortcut.
- Flat ranking weights: results are ranked by consensus across engines,
  not by a manual thumb on the scale.

## How it works

`install.bat` fetches a pinned embeddable Python (SHA256-verified), pip,
and the latest SearXNG master, then applies a handful of Windows
compatibility fixes (SearXNG upstream assumes Linux/Docker); each fix
retires itself automatically if upstream ever ships an equivalent one. All
network access goes through Windows' built-in `curl.exe`, so corporate
proxies and the Windows certificate store are respected. `update.bat`
keeps both SearXNG and this kit current, with automatic rollback if a
SearXNG update fails.

## Credits

- **[SearXNG](https://github.com/searxng/searxng)** - the actual
  metasearch engine doing all the real work (AGPL-3.0). This kit only
  makes it portable on Windows.
- **DysDaemoN** - first beta tester, and the original idea that this
  should be a proper portable app in the first place.

## License

Free software under the [GNU AGPL-3.0](LICENSE) - the same license as
SearXNG itself. SearXNG is not bundled here; the installer downloads
it from the official repository at install time.
