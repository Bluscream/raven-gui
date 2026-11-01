"""Raven command lines and snapshots."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from raven_gui.core.apps import App, DesktopMode
from raven_gui.core.command import (
    RUN_TIMEOUT_MS,
    Snapshot,
    SnapshotKind,
    delete_snapshot,
    list_snapshots,
    rebuild_command,
    restore_command,
    run_app,
    run_program,
    snapshot_command,
)
from raven_gui.core.settings import Settings


def test_run_program_puts_options_in_ravens_order(settings: Settings, app: App) -> None:
    program = app.prefix / "drive_c/App/app.exe"
    invocation = run_program(settings, app, program, ["/silent", "a b"])
    assert invocation.argv == (
        "/opt/raven/raven",
        "--run-process",
        "--execution=native",
        f"--timeout-ms={RUN_TIMEOUT_MS}",
        "--desktop=wayland",
        str(program),
        "--",
        "/silent",
        "a b",
    )
    assert invocation.environment["RAVEN_PREFIX"] == str(app.prefix)
    assert invocation.cwd == program.parent


def test_timeout_is_the_longest_raven_accepts() -> None:
    # Raven rejects anything outside 1..86400000 and defaults to five seconds without one.
    assert RUN_TIMEOUT_MS == 86_400_000


def test_no_desktop_leaves_the_option_out(settings: Settings, app: App) -> None:
    invocation = run_program(settings, replace(app, desktop=DesktopMode.NONE), Path("/x.exe"))
    assert not any(argument.startswith("--desktop") for argument in invocation.argv)
    assert "--" not in invocation.argv


def test_app_environment_cannot_override_the_prefix(settings: Settings, app: App) -> None:
    sneaky = replace(app, environment={"RAVEN_PREFIX": "/elsewhere", "RAVEN_THEME": "classic"})
    environment = run_program(settings, sneaky, Path("/x.exe")).environment
    assert environment == {"RAVEN_PREFIX": str(app.prefix), "RAVEN_THEME": "classic"}


def test_run_app_needs_a_program(settings: Settings, app: App) -> None:
    with pytest.raises(ValueError, match="no program"):
        run_app(settings, app)
    executable = Path("/p/app.exe")
    invocation = run_app(settings, replace(app, executable=executable, arguments=("-x",)))
    assert invocation.argv[-3:] == (str(executable), "--", "-x")


def test_snapshot_and_restore_commands(settings: Settings, app: App) -> None:
    assert snapshot_command(settings, app, "before-update").argv == (
        "/opt/raven/raven",
        "--snapshot-prefix",
        "before-update",
    )
    assert restore_command(settings, app, None).argv == ("/opt/raven/raven", "--restore-prefix")
    assert restore_command(settings, app, "20261101-120000-manual").argv[-1] == "20261101-120000-manual"


def test_rebuild_never_pastes_the_path_into_the_script(settings: Settings, tmp_path: Path) -> None:
    source = tmp_path / 'it\'s "raven"; rm -rf ~'
    plain = rebuild_command(replace(settings, source_dir=source))
    assert plain.argv[0] == "sh"
    assert plain.argv[-1] == str(source)
    assert str(source) not in plain.argv[2]
    boxed = rebuild_command(replace(settings, source_dir=source, build_box="raven-box"))
    assert boxed.argv[:5] == ("distrobox", "enter", "raven-box", "--", "sh")


def test_rebuild_needs_a_source_directory(settings: Settings) -> None:
    with pytest.raises(ValueError, match="source directory"):
        rebuild_command(settings)


STAMP = datetime(2026, 11, 1, 22, 33, 44)  # noqa: DTZ001  # Raven stamps snapshots in naive local time


@pytest.mark.parametrize(
    ("name", "label", "kind", "taken"),
    [
        ("20261101-223344-install-setup", "install-setup", SnapshotKind.INSTALL, STAMP),
        ("20261101-223344-before-restore~2", "before-restore", SnapshotKind.BEFORE_RESTORE, STAMP),
        ("20261101-223344-manual", "manual", SnapshotKind.MANUAL, STAMP),
        ("hand-made", "hand-made", SnapshotKind.MANUAL, None),
    ],
)
def test_snapshot_names_parse(name: str, label: str, kind: SnapshotKind, taken: datetime | None) -> None:
    snapshot = Snapshot.from_name(name)
    assert (snapshot.label, snapshot.kind, snapshot.taken) == (label, kind, taken)


def test_list_snapshots_is_newest_first_and_skips_partial_ones(app: App) -> None:
    for name in ("20261101-100000-a", "20261102-100000-b", "20261103-100000-c.partial"):
        (app.snapshots_dir / name).mkdir(parents=True)
    (app.snapshots_dir / "stray-file").write_text("", encoding="utf-8")
    assert [snapshot.name for snapshot in list_snapshots(app)] == ["20261102-100000-b", "20261101-100000-a"]


def test_list_snapshots_without_any(app: App) -> None:
    assert list_snapshots(app) == []


def test_delete_snapshot_stays_inside_the_snapshot_directory(app: App) -> None:
    (app.snapshots_dir / "20261101-100000-a").mkdir(parents=True)
    outside = app.prefix / "drive_c"
    outside.mkdir()
    with pytest.raises(ValueError, match="not a snapshot"):
        delete_snapshot(app, "../notepad/drive_c")
    assert outside.is_dir()
    delete_snapshot(app, "20261101-100000-a")
    assert list_snapshots(app) == []
