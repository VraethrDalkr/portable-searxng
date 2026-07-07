# PortableSearXNG

A fully portable [SearXNG](https://github.com/searxng/searxng) metasearch
instance for Windows — no admin rights, no system installation, no Docker.
Everything lives in one folder that you can move, rename, copy to another
PC, or run from a USB stick.

It queries several search engines on your behalf and shows combined
results without tracking you or building a profile.

## Requirements

- Windows 10 1803 or newer (needs the built-in `curl.exe` / `tar.exe`)
- An internet connection for the first install (~120 MB: portable Python
  from python.org, SearXNG from GitHub, dependencies from PyPI)

## Quick start

1. Download the ZIP: **Code → Download ZIP** (or grab the latest
   [release](../../releases)).
2. **Important:** right-click the downloaded ZIP → Properties → check
   **Unblock** → OK, *before* extracting. This avoids SmartScreen
   warnings when running the .bat files.
3. Extract the folder anywhere — spaces and parentheses in the path are
   fine.
4. Run `install.bat` and wait. When it finishes, your browser opens on
   your own private search page.

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
```

The `browser` setting is handy for a portable browser that travels on
the same USB stick. Personal search preferences (theme, engines per
query, etc.) are set in the web UI and live in your browser's cookies;
instance-wide defaults live in `settings.yml`.

See `README.txt` inside the kit for the full details: engine selection
rationale, bang shortcuts for the disabled big engines (`!goc`, `!bi`,
`!yd`), how updates treat your edited files, and known caveats.

## Privacy defaults

- Binds to `127.0.0.1` only — not reachable from the network.
- Independent/privacy-respecting engines enabled (Mojeek, Brave, Qwant,
  Mwmbl, DuckDuckGo, Startpage, Wikipedia/Wikidata).
- Google (CSE), Bing, and Yandex are disabled by default and only run
  when you explicitly ask via their bang shortcut.
- Flat ranking weights: results are ranked by consensus across engines,
  not by a manual thumb on the scale.

## How it works

`install.bat` fetches a pinned embeddable Python (SHA256-verified), pip,
and the latest SearXNG master, then applies a handful of Windows
compatibility fixes (SearXNG upstream assumes Linux/Docker). All
network access goes through Windows' built-in `curl.exe`, so corporate
proxies and the Windows certificate store are respected. `update.bat`
keeps both SearXNG and this kit current, with automatic rollback if a
SearXNG update fails.
