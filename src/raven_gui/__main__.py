"""Command line: start the window, open a Windows program in it, or start an app without any window of our own."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

from raven_gui.core import RavenGuiError
from raven_gui.core.apps import AppId, AppStore
from raven_gui.core.command import run_app
from raven_gui.core.desktop import install_front_end_entry
from raven_gui.core.settings import load_settings

logger = logging.getLogger(__name__)


def launcher_command() -> list[str]:
    """Return how menu entries start this front end: the installed command when there is one."""
    installed = shutil.which("raven-gui")
    return [installed] if installed else [sys.executable, "-m", "raven_gui"]


def launch(app_id: str) -> int:
    """Replace this process with Raven running the app, so a menu entry costs no window of ours."""
    settings = load_settings()
    app = AppStore().get(AppId(app_id))
    invocation = run_app(settings, app)
    os.chdir(invocation.cwd)
    os.execvpe(invocation.argv[0], invocation.argv, invocation.full_environment())  # noqa: S606  # argv built from the user's own app record, no shell


def build_parser() -> argparse.ArgumentParser:
    """Return the command line parser."""
    parser = argparse.ArgumentParser(prog="raven-gui", description="Install and run Windows programs with Raven.")
    # A plain optional argument, so a menu entry's "%f" can expand to nothing when started without a file.
    parser.add_argument("file", nargs="?", type=Path, help="a Windows program or installer to install or run")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--launch", metavar="APP", help="start an app by its id, without opening the window")
    group.add_argument("--open", metavar="FILE", type=Path, help="the same as giving FILE")
    group.add_argument(
        "--install-menu-entry",
        action="store_true",
        help="add the front end to the menu and to Open With for .exe files",
    )
    parser.add_argument("--verbose", action="store_true", help="log debug messages")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and do what it asks."""
    args = build_parser().parse_args(argv)
    file: Path | None = args.file or args.open
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    try:
        if args.launch:
            return launch(args.launch)
        if args.install_menu_entry:
            logger.info("Wrote %s", install_front_end_entry(launcher_command()))
            return 0
    except (RavenGuiError, ValueError, OSError) as error:
        logger.error("%s", error)  # noqa: TRY400  # the message is the whole story for a command line user
        return 1

    # Qt loads only for the window, so --launch stays quick.
    from raven_gui.ui.application import run_window  # noqa: PLC0415

    return run_window(open_file=file.resolve() if file else None, launcher=launcher_command())


if __name__ == "__main__":
    sys.exit(main())
