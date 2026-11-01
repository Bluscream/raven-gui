"""Settings persistence."""

from __future__ import annotations

from pathlib import Path

from raven_gui.core.settings import Settings, load_settings, save_settings, settings_path


def test_missing_file_gives_defaults() -> None:
    assert load_settings() == Settings.defaults()


def test_round_trip(tmp_path: Path) -> None:
    settings = Settings(
        raven_binary=tmp_path / "raven",
        prefixes_root=tmp_path / "p",
        source_dir=tmp_path / "src",
        build_box="raven-box",
    )
    save_settings(settings)
    assert settings_path().is_file()
    assert load_settings() == settings


def test_unreadable_file_gives_defaults() -> None:
    settings_path().parent.mkdir(parents=True)
    settings_path().write_text("[1, 2", encoding="utf-8")
    assert load_settings() == Settings.defaults()
    settings_path().write_text("[1, 2]", encoding="utf-8")
    assert load_settings() == Settings.defaults()


def test_partial_file_fills_in_defaults() -> None:
    settings_path().parent.mkdir(parents=True)
    settings_path().write_text('{"build_box": "box"}', encoding="utf-8")
    loaded = load_settings()
    assert loaded.build_box == "box"
    assert loaded.prefixes_root == Settings.defaults().prefixes_root
    assert loaded.source_dir is None
