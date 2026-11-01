"""Shared fixtures: every test gets its own XDG directories, so nothing touches the user's real ones."""

from __future__ import annotations

from pathlib import Path

import pytest

from raven_gui.core.apps import App, AppId, AppStore
from raven_gui.core.settings import Settings


@pytest.fixture(autouse=True)
def isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the XDG directories into the test's temporary directory."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Return settings with a made-up Raven and a temporary prefixes directory."""
    return Settings(
        raven_binary=Path("/opt/raven/raven"), prefixes_root=tmp_path / "prefixes", source_dir=None, build_box=""
    )


@pytest.fixture
def store(tmp_path: Path) -> AppStore:
    """Return a store in a temporary directory."""
    return AppStore(tmp_path / "apps")


@pytest.fixture
def app(store: AppStore, settings: Settings) -> App:
    """Return a freshly created app with an empty prefix."""
    created = store.create("Notepad++", settings.prefixes_root)
    assert created.id == AppId("notepad")
    return created
