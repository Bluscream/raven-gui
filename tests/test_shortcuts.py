"""Finding installed programs through shortcuts and on disk."""

from __future__ import annotations

from pathlib import Path

import pylnk3
import pytest

from raven_gui.core.shortcuts import find_programs, programs_on_disk, resolve_windows_path, shortcut_target

START_MENU = "drive_c/ProgramData/Microsoft/Windows/Start Menu/Programs"


def _file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"MZ")
    return path


def _shortcut(path: Path, target: str, arguments: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pylnk3.for_file(target, str(path), arguments=arguments)
    return path


def test_resolve_matches_names_regardless_of_case(tmp_path: Path) -> None:
    program = _file(tmp_path / "drive_c/Program Files/Foo App/Foo.exe")
    assert resolve_windows_path(tmp_path, r"c:\PROGRAM FILES\foo app\foo.EXE") == program
    assert resolve_windows_path(tmp_path, '"C:\\Program Files\\Foo App\\Foo.exe"') == program


def test_resolve_refuses_what_raven_refuses(tmp_path: Path) -> None:
    _file(tmp_path / "drive_c/a.exe")
    assert resolve_windows_path(tmp_path, r"C:\Windows\..\a.exe") is None
    assert resolve_windows_path(tmp_path, r"\\server\share\a.exe") is None
    assert resolve_windows_path(tmp_path, "relative.exe") is None
    assert resolve_windows_path(tmp_path, "C:\\") is None
    assert resolve_windows_path(tmp_path, r"D:\missing.exe") is None


def test_shortcut_target_without_link_info(tmp_path: Path) -> None:
    # pylnk3 writes only shell items, the harder of the two ways a shortcut can name its target.
    shortcut = _shortcut(tmp_path / "foo.lnk", r"C:\Program Files\Foo App\foo.exe", "--fast")
    assert shortcut_target(shortcut) == (r"C:\Program Files\Foo App\foo.exe", "--fast")


def test_shortcut_target_of_garbage(tmp_path: Path) -> None:
    garbage = tmp_path / "bad.lnk"
    garbage.write_bytes(b"\x00" * 10)
    with pytest.warns(UserWarning, match="size must be 76"):
        assert shortcut_target(garbage) is None


def test_find_programs_puts_shortcuts_first_and_noise_last(tmp_path: Path) -> None:
    app = _file(tmp_path / "drive_c/Program Files/Foo/foo.exe")
    _file(tmp_path / "drive_c/Program Files/Foo/unins000.exe")
    _file(tmp_path / "drive_c/Program Files/Foo/tools/bar.exe")
    _shortcut(tmp_path / START_MENU / "Foo/Foo.lnk", r"C:\Program Files\Foo\foo.exe", "-x")
    _shortcut(tmp_path / START_MENU / "Foo/Uninstall Foo.lnk", r"C:\Program Files\Foo\unins000.exe")
    _shortcut(tmp_path / START_MENU / "Foo/Readme.lnk", r"C:\Program Files\Foo\readme.txt")
    _shortcut(tmp_path / "drive_c/Users/someone/Desktop/Foo.lnk", r"C:\Program Files\Foo\foo.exe")

    programs = find_programs(tmp_path)
    assert [(program.name, program.from_shortcut) for program in programs] == [
        ("Foo", True),
        ("Uninstall Foo", True),
        ("bar", False),
    ]
    assert programs[0].path == app
    assert programs[0].arguments == "-x"


def test_programs_on_disk_ignores_windows_and_stops_at_the_limit(tmp_path: Path) -> None:
    _file(tmp_path / "drive_c/windows/system32/notepad.exe")
    for index in range(5):
        _file(tmp_path / f"drive_c/Program Files/App{index}/app{index}.exe")
    assert len(programs_on_disk(tmp_path, limit=3)) == 3
    assert all("windows" not in str(program.path) for program in programs_on_disk(tmp_path))


def test_find_programs_in_an_empty_prefix(tmp_path: Path) -> None:
    assert find_programs(tmp_path) == []
