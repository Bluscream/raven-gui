"""Menu entries."""

from __future__ import annotations

import configparser
from dataclasses import replace
from pathlib import Path

import pytest

from raven_gui.core.apps import App
from raven_gui.core.desktop import (
    WINDOWS_MIME_TYPES,
    app_entry_path,
    exec_line,
    install_app_entry,
    install_front_end_entry,
    remove_app_entry,
)

LAUNCHER = ["/home/me/My Apps/raven-gui"]


def _read(path: Path) -> configparser.SectionProxy:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # type: ignore[assignment,method-assign]  # desktop keys are case-sensitive
    parser.read(path, encoding="utf-8")
    return parser["Desktop Entry"]


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["plain", "--launch", "app"], "plain --launch app"),
        (["/with space/x"], '"/with space/x"'),
        # Quoting escapes " ` $ \ with a backslash, then the file's string escape doubles every backslash.
        (['quote"d', "dollar$", "tick`"], r'"quote\\"d" "dollar\\$" "tick\\`"'),
        # A literal backslash in a quoted argument takes four, as the specification spells out.
        (["back\\slash"], r'"back\\\\slash"'),
        # A percent sign would start a field code.
        (["100%"], "100%%"),
    ],
)
def test_exec_line_follows_the_desktop_entry_specification(arguments: list[str], expected: str) -> None:
    assert exec_line(arguments) == expected


def test_app_entry_launches_through_the_front_end(app: App, tmp_path: Path) -> None:
    named = replace(app, name="Note\npad", executable=tmp_path / "x.exe")
    path = install_app_entry(named, LAUNCHER, icon=None)
    assert path == app_entry_path(app)
    entry = _read(path)
    assert entry["Exec"] == '"/home/me/My Apps/raven-gui" --launch notepad'
    assert entry["Name"] == "Note\\npad"
    assert entry["Icon"] == "application-x-ms-dos-executable"


def test_app_entry_uses_an_existing_icon(app: App, tmp_path: Path) -> None:
    icon = tmp_path / "icon.png"
    icon.write_bytes(b"png")
    assert _read(install_app_entry(app, LAUNCHER, icon))["Icon"] == str(icon)


def test_remove_app_entry(app: App) -> None:
    install_app_entry(app, LAUNCHER, icon=None)
    remove_app_entry(app)
    assert not app_entry_path(app).exists()
    remove_app_entry(app)


def test_front_end_entry_opens_windows_programs() -> None:
    entry = _read(install_front_end_entry(LAUNCHER))
    assert entry["Exec"].endswith(" --open %f")
    assert entry["MimeType"] == ";".join(WINDOWS_MIME_TYPES) + ";"
