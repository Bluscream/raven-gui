"""Starting the Qt application and loading the Kirigami window."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine, QQmlError
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from raven_gui import APP_ID, APP_NAME
from raven_gui.ui.backend import Backend

logger = logging.getLogger(__name__)

QML_DIR = Path(__file__).resolve().parent.parent / "qml"


def _log_qml_warnings(errors: list[QQmlError]) -> None:
    for error in errors:
        logger.warning("%s", error.toString())


def run_window(open_file: Path | None, launcher: list[str]) -> int:
    """Show the window until it closes and return the exit code."""
    # Plasma's own controls style, so the window looks like the rest of the desktop; QML falls back to its default elsewhere.
    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle("org.kde.desktop")
    # QApplication rather than QGuiApplication: the desktop style draws its controls with the widget style.
    app = QApplication(sys.argv)
    app.setApplicationName("raven-gui")
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationDomain("bluscream.org")
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(QIcon.fromTheme("wine"))

    backend = Backend(launcher)
    engine = QQmlApplicationEngine()
    engine.warnings.connect(_log_qml_warnings)
    engine.setInitialProperties({"backend": backend, "openFile": str(open_file) if open_file else ""})
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        logger.error("The window could not be loaded; see the QML errors above.")
        return 1
    app.aboutToQuit.connect(backend.shutdown)
    return app.exec()
