"""The Raven command lines this front end runs, built in the one place that knows Raven's argument order."""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from raven_gui.core.apps import App, DesktopMode
from raven_gui.core.settings import Settings

# The longest run Raven accepts. Without a timeout Raven ends the program after five seconds, which suits its
# test fixtures and no desktop program.
RUN_TIMEOUT_MS = 86_400_000

_SNAPSHOT_NAME = re.compile(r"^(?P<stamp>\d{8}-\d{6})-(?P<label>.+?)(?:~\d+)?$")


@dataclass(frozen=True, slots=True)
class Invocation:
    """A process to start: its arguments, the environment it adds, and where it starts."""

    argv: tuple[str, ...]
    environment: Mapping[str, str]
    cwd: Path

    def full_environment(self) -> dict[str, str]:
        """Return the current environment with this invocation's additions."""
        return {**os.environ, **self.environment}


def _prefix_environment(app: App) -> dict[str, str]:
    return {**app.environment, "RAVEN_PREFIX": str(app.prefix)}


def run_program(settings: Settings, app: App, program: Path, arguments: Sequence[str] = ()) -> Invocation:
    """Return the command that runs a Windows program in the app's prefix."""
    # Raven reads its options by position: the timeout, then the desktop, then the program and its arguments.
    argv = [str(settings.raven_binary), "--run-process", "--execution=native", f"--timeout-ms={RUN_TIMEOUT_MS}"]
    if app.desktop is not DesktopMode.NONE:
        argv.append(f"--desktop={app.desktop.value}")
    argv.append(str(program))
    if arguments:
        argv += ["--", *arguments]
    return Invocation(tuple(argv), _prefix_environment(app), program.parent)


def run_app(settings: Settings, app: App) -> Invocation:
    """Return the command that starts the app's chosen program."""
    if app.executable is None:
        msg = f"{app.name} has no program to start yet."
        raise ValueError(msg)
    return run_program(settings, app, app.executable, app.arguments)


def snapshot_command(settings: Settings, app: App, label: str) -> Invocation:
    """Return the command that takes a snapshot of the app's prefix."""
    return Invocation((str(settings.raven_binary), "--snapshot-prefix", label), _prefix_environment(app), app.prefix)


def restore_command(settings: Settings, app: App, snapshot: str | None) -> Invocation:
    """Return the command that restores a snapshot, the newest one when none is named."""
    argv = (str(settings.raven_binary), "--restore-prefix", *([snapshot] if snapshot else []))
    return Invocation(argv, _prefix_environment(app), app.prefix)


# The source directory arrives as $1, so no path is ever pasted into the script.
_REBUILD_SCRIPT = 'set -e; cd "$1"; git pull --ff-only; cmake --build build -j"$(nproc)"'


def rebuild_command(settings: Settings) -> Invocation:
    """Return the command that updates Raven's sources and rebuilds it, inside the build container when one is set."""
    if settings.source_dir is None:
        msg = "Set the Raven source directory first."
        raise ValueError(msg)
    script = ("sh", "-c", _REBUILD_SCRIPT, "raven-rebuild", str(settings.source_dir))
    argv = ("distrobox", "enter", settings.build_box, "--", *script) if settings.build_box else script
    return Invocation(argv, {}, settings.source_dir)


class SnapshotKind(StrEnum):
    """Why a snapshot was taken, as far as its label tells."""

    INSTALL = "install"
    BEFORE_RESTORE = "before-restore"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class Snapshot:
    """One saved state of a prefix."""

    name: str
    label: str
    taken: datetime | None

    @property
    def kind(self) -> SnapshotKind:
        """Return why the snapshot was taken."""
        if self.label.startswith("install-"):
            return SnapshotKind.INSTALL
        if self.label == "before-restore":
            return SnapshotKind.BEFORE_RESTORE
        return SnapshotKind.MANUAL

    @classmethod
    def from_name(cls, name: str) -> Snapshot:
        """Parse a name Raven gave a snapshot: a local time stamp, a label and maybe a counter."""
        match = _SNAPSHOT_NAME.match(name)
        if not match:
            return cls(name=name, label=name, taken=None)
        # Raven stamps snapshots in local time without a zone; the naive value is the honest reading of it.
        taken = datetime.strptime(match["stamp"], "%Y%m%d-%H%M%S")  # noqa: DTZ007
        return cls(name=name, label=match["label"], taken=taken)


def list_snapshots(app: App) -> list[Snapshot]:
    """Return the app's snapshots, newest first, read from the directory Raven keeps them in."""
    if not app.snapshots_dir.is_dir():
        return []
    names = [path.name for path in app.snapshots_dir.iterdir() if path.is_dir() and path.suffix != ".partial"]
    return [Snapshot.from_name(name) for name in sorted(names, reverse=True)]


def delete_snapshot(app: App, name: str) -> None:
    """Delete one snapshot; Raven has no command for it, and its snapshots share unchanged files only by hard link."""
    target = app.snapshots_dir / name
    if target.parent != app.snapshots_dir or not target.is_dir():
        msg = f"{name} is not a snapshot of {app.name}."
        raise ValueError(msg)
    shutil.rmtree(target)
