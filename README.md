# Raven GUI

A KDE desktop front end for [Raven](https://github.com/mirkobrombin/raven), the Windows compatibility layer for Linux by Mirko Brombin. Raven itself is a command-line program; this gives it a window, in the spirit of Bottles.

It is an unofficial project and not affiliated with Raven.

## What it does

- **An app library.** Every app gets a prefix of its own (its own `C:` drive and registry), shown as a tile with the program's own icon.
- **Installing.** Pick a `setup.exe` or `.msi` and it runs in a fresh prefix. When the installer closes, the programs it left behind are listed from their Start Menu and desktop shortcuts, so you can pick the one to start. Portable programs can be added as they are.
- **Running.** Play and stop, with Raven's output in a live log. Windows go to Wayland, X11 (experimental in Raven), or nowhere for console programs. Per-app environment variables, such as `RAVEN_THEME=classic`.
- **Snapshots.** Take, restore and delete them. Raven takes one by itself before a recognised installer, and before every restore.
- **The desktop.** An app can get its own menu entry, which starts it without opening this window. The front end can also register itself for Open With on `.exe` and `.msi` files.
- **Updating Raven.** Pull and rebuild Raven from its source checkout, optionally inside a distrobox.

## Requirements

- Raven, built from source as its README describes.
- Python 3.12 or newer, with PySide6 from your distribution (`python3-pyside6` on Fedora). A PySide6 wheel from PyPI will not do: it bundles its own Qt, which cannot load the system's Kirigami.
- Kirigami and Kirigami Addons for Qt 6 (`kf6-kirigami`, `kf6-kirigami-addons`), which every Plasma 6 desktop has.
- `desktop-file-utils` for the test suite.

## Installing

```sh
git clone https://github.com/Bluscream/raven-gui.git
cd raven-gui
python3 -m venv --system-site-packages .venv   # system site packages, for the distribution's PySide6
.venv/bin/python -m pip install -e . --group dev
ln -s "$PWD/bin/raven-gui" ~/.local/bin/raven-gui
raven-gui --install-menu-entry                  # optional: menu entry and Open With for .exe files
```

Then start **Raven** from the menu, or `raven-gui`. Point the settings at Raven's binary (`build/native/raven` in its checkout) if it is not on your `PATH`.

## Command line

```text
raven-gui                      open the window
raven-gui --open setup.exe     open the window ready to install or run a program
raven-gui --launch APP_ID      start an app without opening the window (what menu entries run)
raven-gui --install-menu-entry add the front end to the menu and to Open With
```

## Where things are kept

| What | Where |
| :--- | :--- |
| Settings | `~/.config/raven-gui/settings.json` |
| App records | `~/.local/share/raven-gui/apps/<id>.json` |
| Icons | `~/.local/share/raven-gui/icons/<id>.png` |
| Prefixes | `~/.local/share/raven/<id>` by default; Raven keeps snapshots beside each, in `<id>.snapshots` |

## Development

```sh
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy && .venv/bin/pytest
```

The same gate runs through `pre-commit`. The code is split into `raven_gui.core`, which needs no Qt (settings, apps, Raven command lines, shortcuts, icons, menu entries), and `raven_gui.ui` plus the QML in `raven_gui/qml`, which only present it.

`tests/fixtures/icon-program` holds a tiny Windows program whose only content is an icon; `build.sh` there rebuilds it with MinGW-w64.

## License

MIT. Raven is licensed separately by its authors.
