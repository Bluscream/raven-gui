"""Where Raven lives and where prefixes go, stored as JSON in the XDG config directory."""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def config_home() -> Path:
    """Return the XDG config directory."""
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def data_home() -> Path:
    """Return the XDG data directory."""
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")


@dataclass(frozen=True, slots=True)
class Settings:
    """User choices that outlive a session."""

    raven_binary: Path
    prefixes_root: Path
    source_dir: Path | None
    build_box: str

    @classmethod
    def defaults(cls) -> Settings:
        """Return settings that work for a Raven on PATH and Raven's own prefix location."""
        found = shutil.which("raven")
        return cls(
            raven_binary=Path(found) if found else Path.home() / ".local/bin/raven",
            prefixes_root=data_home() / "raven",
            source_dir=None,
            build_box="",
        )


def settings_path() -> Path:
    """Return where the settings file lives."""
    return config_home() / "raven-gui" / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    """Read the settings file, falling back to the defaults for anything missing."""
    path = path or settings_path()
    defaults = Settings.defaults()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return defaults
    except (OSError, json.JSONDecodeError) as error:
        logger.warning("Ignoring unreadable settings file %s: %s", path, error)
        return defaults
    if not isinstance(raw, dict):
        logger.warning("Ignoring settings file %s: it does not hold an object", path)
        return defaults
    source = raw.get("source_dir")
    return Settings(
        raven_binary=Path(str(raw.get("raven_binary", defaults.raven_binary))),
        prefixes_root=Path(str(raw.get("prefixes_root", defaults.prefixes_root))),
        source_dir=Path(str(source)) if source else None,
        build_box=str(raw.get("build_box", defaults.build_box)),
    )


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Write the settings file atomically."""
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {key: str(value) if value is not None else None for key, value in asdict(settings).items()}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
