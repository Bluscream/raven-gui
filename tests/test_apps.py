"""App records: creation, persistence and deletion."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from raven_gui.core.apps import App, AppError, AppStore, DesktopMode, slugify
from raven_gui.core.settings import Settings


def test_slugify_keeps_letters_and_digits() -> None:
    assert slugify("Paint.NET 5") == "paint-net-5"
    assert slugify("  !!!  ") == "app"


def test_create_makes_prefix_and_record(app: App, store: AppStore, settings: Settings) -> None:
    assert app.prefix == settings.prefixes_root / "notepad"
    assert app.prefix.is_dir()
    assert store.get(app.id) == app


def test_create_never_reuses_a_prefix(store: AppStore, settings: Settings) -> None:
    (settings.prefixes_root / "keepass").mkdir(parents=True)
    first = store.create("KeePass", settings.prefixes_root)
    second = store.create("KeePass", settings.prefixes_root)
    assert (first.id, second.id) == ("keepass-2", "keepass-3")


def test_create_rejects_an_empty_name(store: AppStore, settings: Settings) -> None:
    with pytest.raises(AppError):
        store.create("   ", settings.prefixes_root)


def test_record_round_trips_every_field(app: App, store: AppStore) -> None:
    changed = replace(
        app,
        executable=app.prefix / "drive_c/Program Files/Notepad++/notepad++.exe",
        arguments=("-multiInst",),
        desktop=DesktopMode.X11,
        environment={"RAVEN_THEME": "classic"},
    )
    store.save(changed)
    assert store.get(app.id) == changed


def test_list_skips_broken_records(app: App, store: AppStore) -> None:
    (store.directory / "broken.json").write_text("{not json", encoding="utf-8")
    (store.directory / "partial.json").write_text(json.dumps({"id": "x"}), encoding="utf-8")
    assert [listed.id for listed in store.list()] == [app.id]


def test_from_json_rejects_a_bad_desktop() -> None:
    with pytest.raises(AppError):
        App.from_json({"id": "a", "name": "A", "prefix": "/p", "desktop": "mir"})


def test_delete_keeps_or_removes_the_prefix(store: AppStore, settings: Settings) -> None:
    kept = store.create("Kept", settings.prefixes_root)
    store.delete(kept, remove_prefix=False)
    assert kept.prefix.is_dir()
    assert store.list() == []

    removed = store.create("Removed", settings.prefixes_root)
    removed.snapshots_dir.mkdir()
    store.delete(removed, remove_prefix=True)
    assert not removed.prefix.exists()
    assert not removed.snapshots_dir.exists()


def test_snapshots_dir_is_a_sibling_named_after_the_prefix(app: App) -> None:
    assert app.snapshots_dir == app.prefix.parent / "notepad.snapshots"


def test_installed_follows_the_executable(app: App) -> None:
    assert not app.installed
    assert replace(app, executable=Path("/x.exe")).installed
