"""Menu entries: one per app, and one for the front end that opens Windows programs from the file manager."""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from raven_gui import APP_ID, APP_NAME
from raven_gui.core.apps import App
from raven_gui.core.settings import data_home

logger = logging.getLogger(__name__)

# The types file managers give Windows programs, installer packages and shortcuts.
WINDOWS_MIME_TYPES = (
    "application/x-ms-dos-executable",
    "application/x-msdownload",
    "application/vnd.microsoft.portable-executable",
    "application/x-msi",
    "application/x-ms-shortcut",
)

_PREFIX = "raven-gui-app-"


def applications_dir() -> Path:
    """Return the per-user directory menu entries go in."""
    return data_home() / "applications"


def icons_dir() -> Path:
    """Return where app icons are kept as PNG files."""
    return data_home() / "raven-gui" / "icons"


def quote_exec_argument(argument: str) -> str:
    """Quote one argument of an Exec key as the desktop entry specification asks."""
    if argument and not any(character in argument for character in " \t\n\"'\\><~|&;$*?#()`"):
        return argument.replace("%", "%%")
    escaped = argument.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return '"' + escaped.replace("%", "%%") + '"'


def exec_line(arguments: Sequence[str]) -> str:
    """Join arguments into an Exec value, escaped for the file as well as quoted for the command line."""
    # The string escapes of every value apply before the quoting: a literal backslash in a quoted argument ends as four.
    return _escape_value(" ".join(quote_exec_argument(argument) for argument in arguments))


def _escape_value(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def app_entry_path(app: App) -> Path:
    """Return the path of an app's menu entry."""
    return applications_dir() / f"{_PREFIX}{app.id}.desktop"


def app_entry(app: App, launcher: Sequence[str], icon: Path | None) -> str:
    """Return the menu entry that starts an app through the front end's --launch option."""
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={_escape_value(app.name)}",
        f"Comment={_escape_value(f'{app.name}, running in Raven')}",
        f"Exec={exec_line([*launcher, '--launch', app.id])}",
        f"Icon={icon if icon and icon.exists() else 'application-x-ms-dos-executable'}",
        "Terminal=false",
        "Categories=Wine;",
        f"X-Raven-Gui-App={app.id}",
    ]
    return "\n".join(lines) + "\n"


def front_end_entry(launcher: Sequence[str]) -> str:
    """Return the menu entry of the front end itself, which also opens Windows programs given to it."""
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={APP_NAME}",
        "GenericName=Windows program runner",
        "Comment=Install and run Windows programs with Raven",
        f"Exec={exec_line(launcher)} --open %f",
        "Icon=wine",
        "Terminal=false",
        "Categories=System;Emulator;",
        f"MimeType={';'.join(WINDOWS_MIME_TYPES)};",
        f"StartupWMClass={APP_ID}",
    ]
    return "\n".join(lines) + "\n"


def front_end_entry_path() -> Path:
    """Return the path of the front end's own menu entry."""
    return applications_dir() / f"{APP_ID}.desktop"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    _refresh_menu()


def _refresh_menu() -> None:
    """Tell the desktop the entries changed; it notices on its own too, a little later."""
    tool = shutil.which("update-desktop-database")
    if tool is None:
        return
    result = subprocess.run([tool, str(applications_dir())], capture_output=True, text=True, check=False)  # noqa: S603  # fixed tool and our own directory
    if result.returncode:
        logger.warning("update-desktop-database failed: %s", result.stderr.strip())


def install_app_entry(app: App, launcher: Sequence[str], icon: Path | None) -> Path:
    """Write an app's menu entry and return its path."""
    path = app_entry_path(app)
    _write(path, app_entry(app, launcher, icon))
    return path


def remove_app_entry(app: App) -> None:
    """Remove an app's menu entry, if it has one."""
    path = app_entry_path(app)
    if path.exists():
        path.unlink()
        _refresh_menu()


def install_front_end_entry(launcher: Sequence[str]) -> Path:
    """Write the front end's menu entry, which makes it an Open With choice for Windows programs."""
    path = front_end_entry_path()
    _write(path, front_end_entry(launcher))
    return path
