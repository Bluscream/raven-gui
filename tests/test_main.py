"""The command line."""

from __future__ import annotations

from pathlib import Path

import pytest

from raven_gui.__main__ import build_parser


def test_no_arguments_opens_the_window() -> None:
    # Regression: the menu entry ran "--open %f", and with no file %f expands to nothing, leaving --open without its value.
    args = build_parser().parse_args([])
    assert args.file is None
    assert args.open is None


def test_a_file_can_be_given_plainly_or_with_open() -> None:
    assert build_parser().parse_args(["setup.exe"]).file == Path("setup.exe")
    assert build_parser().parse_args(["--open", "setup.exe"]).open == Path("setup.exe")


def test_launch_and_menu_entry_exclude_each_other() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--launch", "app", "--install-menu-entry"])
