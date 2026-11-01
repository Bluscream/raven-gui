"""The apps the user manages: one prefix each, recorded as one JSON file each."""

from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import NewType

from raven_gui.core import RavenGuiError
from raven_gui.core.settings import data_home

logger = logging.getLogger(__name__)

AppId = NewType("AppId", str)

_SLUG_INVALID = re.compile(r"[^a-z0-9]+")


class DesktopMode(StrEnum):
    """How Raven shows the program's windows."""

    WAYLAND = "wayland"
    X11 = "x11"
    NONE = "none"


class AppError(RavenGuiError):
    """An app record could not be created, read or written."""


@dataclass(frozen=True, slots=True)
class App:
    """A Windows program installed in a prefix of its own."""

    id: AppId
    name: str
    prefix: Path
    executable: Path | None = None
    arguments: tuple[str, ...] = ()
    desktop: DesktopMode = DesktopMode.WAYLAND
    environment: dict[str, str] = field(default_factory=dict)

    @property
    def installed(self) -> bool:
        """Whether a program to start has been chosen."""
        return self.executable is not None

    @property
    def snapshots_dir(self) -> Path:
        """Return where Raven keeps the prefix's snapshots: a sibling directory named after it."""
        return self.prefix.parent / (self.prefix.name + ".snapshots")

    def to_json(self) -> dict[str, object]:
        """Return the record as JSON-ready data."""
        return {
            "id": self.id,
            "name": self.name,
            "prefix": str(self.prefix),
            "executable": str(self.executable) if self.executable else None,
            "arguments": list(self.arguments),
            "desktop": self.desktop.value,
            "environment": dict(self.environment),
        }

    @classmethod
    def from_json(cls, data: object) -> App:
        """Parse a record, rejecting anything that is not one."""
        if not isinstance(data, dict):
            msg = "An app record must be a JSON object."
            raise AppError(msg)
        try:
            executable = data.get("executable")
            arguments = data.get("arguments", [])
            environment = data.get("environment", {})
            if not isinstance(arguments, list) or not isinstance(environment, dict):
                msg = "An app record has malformed arguments or environment."
                raise AppError(msg)
            return cls(
                id=AppId(str(data["id"])),
                name=str(data["name"]),
                prefix=Path(str(data["prefix"])),
                executable=Path(str(executable)) if executable else None,
                arguments=tuple(str(argument) for argument in arguments),
                desktop=DesktopMode(str(data.get("desktop", DesktopMode.WAYLAND.value))),
                environment={str(key): str(value) for key, value in environment.items()},
            )
        except (KeyError, ValueError) as error:
            msg = f"An app record is incomplete: {error}."
            raise AppError(msg) from error


def slugify(name: str) -> str:
    """Turn a display name into a directory and file name."""
    return _SLUG_INVALID.sub("-", name.lower()).strip("-") or "app"


class AppStore:
    """Reads and writes the app records in one directory."""

    def __init__(self, directory: Path | None = None) -> None:
        """Use the given directory, or the one in the XDG data directory."""
        self.directory = directory or data_home() / "raven-gui" / "apps"

    def _path(self, app_id: AppId) -> Path:
        return self.directory / f"{app_id}.json"

    def list(self) -> list[App]:
        """Return every readable record, sorted by name; unreadable ones are logged and skipped."""
        apps = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                apps.append(App.from_json(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError, AppError) as error:
                logger.warning("Skipping unreadable app record %s: %s", path, error)
        return sorted(apps, key=lambda app: app.name.casefold())

    def get(self, app_id: AppId) -> App:
        """Return one record."""
        try:
            return App.from_json(json.loads(self._path(app_id).read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as error:
            msg = f"The app {app_id} could not be read: {error}."
            raise AppError(msg) from error

    def save(self, app: App) -> None:
        """Write one record atomically."""
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self._path(app.id).with_suffix(".tmp")
        temporary.write_text(json.dumps(app.to_json(), indent=2) + "\n", encoding="utf-8")
        temporary.replace(self._path(app.id))

    def create(self, name: str, prefixes_root: Path) -> App:
        """Record a new app with a fresh prefix directory of its own."""
        name = name.strip()
        if not name:
            msg = "An app needs a name."
            raise AppError(msg)
        base = slugify(name)
        taken = {app.id for app in self.list()}
        candidate, count = base, 2
        while candidate in taken or (prefixes_root / candidate).exists():
            candidate, count = f"{base}-{count}", count + 1
        app = App(id=AppId(candidate), name=name, prefix=prefixes_root / candidate)
        app.prefix.mkdir(parents=True)
        self.save(app)
        return app

    def delete(self, app: App, *, remove_prefix: bool) -> None:
        """Forget an app and, if asked, delete its prefix and snapshots."""
        self._path(app.id).unlink(missing_ok=True)
        if remove_prefix:
            for directory in (app.prefix, app.snapshots_dir):
                if directory.exists():
                    shutil.rmtree(directory)
