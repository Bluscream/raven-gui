"""Finding the programs an installer put in a prefix, through the shortcuts it made and the files it wrote."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import LnkParse3

logger = logging.getLogger(__name__)

# Where installers put shortcuts, relative to drive C. Per-user folders are searched for every user in the prefix.
_SHARED_SHORTCUT_DIRS = ("ProgramData/Microsoft/Windows/Start Menu/Programs", "Users/Public/Desktop")
_USER_SHORTCUT_DIRS = ("AppData/Roaming/Microsoft/Windows/Start Menu/Programs", "Desktop")
_PROGRAM_DIRS = ("Program Files", "Program Files (x86)", "Users")
# Shortcuts and programs that are almost never what the user wants to start.
_NOISE = ("uninst", "unins0", "setup", "update", "crashreport", "helper", "vc_redist", "dotnet")


@dataclass(frozen=True, slots=True)
class Program:
    """A program in a prefix that the user might want to start."""

    name: str
    path: Path
    arguments: str = ""
    from_shortcut: bool = False


def resolve_windows_path(prefix: Path, windows_path: str) -> Path | None:
    """Map a Windows path to the file in the prefix, as Raven does, but matching names regardless of case."""
    path = PureWindowsPath(windows_path.strip().strip('"'))
    if not path.drive or len(path.drive) != 2 or not path.drive[0].isalpha():  # noqa: PLR2004  # a drive is "X:"
        return None
    parts = path.parts[1:]
    if not parts or ".." in parts:
        return None
    current = prefix / f"drive_{path.drive[0].lower()}"
    for part in parts:
        exact = current / part
        if exact.exists():
            current = exact
            continue
        folded = part.casefold()
        match = next((child for child in _children(current) if child.name.casefold() == folded), None)
        if match is None:
            return None
        current = match
    return current


def _children(directory: Path) -> list[Path]:
    try:
        return list(directory.iterdir())
    except OSError:
        return []


def shortcut_target(shortcut: Path) -> tuple[str, str] | None:
    """Return the Windows path a shortcut points at and its arguments, or None when it does not point at a file."""
    try:
        with shortcut.open("rb") as handle:
            parsed = LnkParse3.lnk_file(handle).get_json()
    except Exception as error:  # noqa: BLE001  # LnkParse3 raises bare exceptions of many kinds on malformed files
        logger.warning("Skipping unreadable shortcut %s: %s", shortcut, error)
        return None
    arguments = str(parsed.get("data", {}).get("command_line_arguments") or "")
    info = parsed.get("link_info", {})
    base = info.get("local_base_path_unicode") or info.get("local_base_path")
    if base:
        suffix = info.get("common_path_suffix_unicode") or info.get("common_path_suffix") or ""
        return str(PureWindowsPath(base) / suffix) if suffix else str(base), arguments
    # Without link information the target is spelled out by the shell items: a volume, then one name per folder.
    names: list[str] = []
    for item in parsed.get("target", {}).get("items", []):
        if item.get("class") == "Volume Item":
            names = [str(item.get("volume_name", ""))]
        elif item.get("class") == "File entry" and names:
            names.append(str(item.get("long_name") or item.get("primary_name") or ""))
    if len(names) < 2:  # noqa: PLR2004  # a volume and at least one name
        return None
    return str(PureWindowsPath(*names)), arguments


def _is_noise(name: str) -> bool:
    folded = name.casefold()
    return any(word in folded for word in _NOISE)


def _shortcut_dirs(prefix: Path) -> list[Path]:
    drive = prefix / "drive_c"
    dirs = [drive / relative for relative in _SHARED_SHORTCUT_DIRS]
    for user in _children(drive / "Users"):
        dirs += [user / relative for relative in _USER_SHORTCUT_DIRS]
    return [directory for directory in dirs if directory.is_dir()]


def programs_from_shortcuts(prefix: Path) -> list[Program]:
    """Return the programs the prefix's Start Menu and desktop shortcuts point at."""
    found: dict[Path, Program] = {}
    for directory in _shortcut_dirs(prefix):
        for shortcut in sorted(directory.rglob("*.lnk")):
            target = shortcut_target(shortcut)
            if target is None:
                continue
            path = resolve_windows_path(prefix, target[0])
            if path is None or path.suffix.lower() != ".exe" or not path.is_file():
                continue
            found.setdefault(path, Program(name=shortcut.stem, path=path, arguments=target[1], from_shortcut=True))
    return sorted(found.values(), key=lambda program: (_is_noise(program.name), program.name.casefold()))


def programs_on_disk(prefix: Path, limit: int = 200) -> list[Program]:
    """Return the programs installed under Program Files and the user folders, for installers that make no shortcut."""
    drive = prefix / "drive_c"
    found: list[Program] = []
    roots = [drive / relative for relative in _PROGRAM_DIRS if (drive / relative).is_dir()]
    for path in (path for root in roots for path in sorted(root.rglob("*"))):
        if path.suffix.lower() == ".exe" and path.is_file():
            found.append(Program(name=path.stem, path=path))
            if len(found) >= limit:
                break
    return sorted(found, key=lambda program: (_is_noise(program.name), program.name.casefold()))


def find_programs(prefix: Path) -> list[Program]:
    """Return the programs worth offering after an installation: shortcut targets first, then other programs."""
    shortcuts = programs_from_shortcuts(prefix)
    known = {program.path for program in shortcuts}
    return shortcuts + [program for program in programs_on_disk(prefix) if program.path not in known]
