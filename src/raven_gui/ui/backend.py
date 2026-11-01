"""The object QML talks to: every action the window offers, on top of the Qt-free core."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Property, QBuffer, QByteArray, QIODevice, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QImage, QImageReader

from raven_gui.core import RavenGuiError
from raven_gui.core.apps import App, AppId, AppStore, DesktopMode
from raven_gui.core.command import (
    Invocation,
    delete_snapshot,
    list_snapshots,
    rebuild_command,
    restore_command,
    run_app,
    run_program,
    snapshot_command,
)
from raven_gui.core.desktop import (
    app_entry_path,
    icons_dir,
    install_app_entry,
    install_front_end_entry,
    remove_app_entry,
)
from raven_gui.core.icons import extract_icon
from raven_gui.core.settings import Settings, load_settings, save_settings
from raven_gui.core.shortcuts import find_programs
from raven_gui.ui.models import AppListModel
from raven_gui.ui.processes import ProcessRunner

logger = logging.getLogger(__name__)

REBUILD_KEY = "rebuild"


def _path(text: str) -> Path:
    """Accept a plain path or a file URL from a QML file dialog."""
    return Path(QUrl(text).toLocalFile()) if text.startswith("file:") else Path(text).expanduser()


def _png_from_ico(ico: bytes) -> QImage | None:
    """Return the largest image in an .ico file."""
    buffer = QBuffer()
    buffer.setData(QByteArray(ico))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer, QByteArray(b"ico"))
    best: QImage | None = None
    for index in range(max(reader.imageCount(), 1)):
        reader.jumpToImage(index)
        image = reader.read()
        if not image.isNull() and (best is None or image.width() > best.width()):
            best = image
    return best


class Backend(QObject):
    """Apps, their prefixes and processes, snapshots, menu entries and settings."""

    message = Signal(str, bool)  # text, is an error
    logAppended = Signal(str, str)  # key, text
    runningChanged = Signal(str, bool)  # key, running
    installFinished = Signal(str, list)  # app id, programs found
    snapshotsChanged = Signal(str)  # app id
    appChanged = Signal(str)  # app id
    settingsChanged = Signal()

    def __init__(self, launcher: list[str], parent: QObject | None = None) -> None:
        """Load settings and apps; launcher is how menu entries start this front end."""
        super().__init__(parent)
        self._launcher = launcher
        self._settings = load_settings()
        self._store = AppStore()
        self._model = AppListModel(icons_dir(), self)
        self._runner = ProcessRunner(self)
        self._runner.output.connect(self.logAppended)
        self._runner.stateChanged.connect(self._state_changed)
        self._reload()

    # ---- helpers ----

    def _reload(self) -> None:
        self._model.reset(self._store.list())

    def _app(self, app_id: str) -> App | None:
        try:
            return self._store.get(AppId(app_id))
        except RavenGuiError as error:
            self.message.emit(str(error), True)
            return None

    def _state_changed(self, key: str, running: bool) -> None:  # noqa: FBT001  # mirrors the Qt signal's arguments
        if key.startswith("app:"):
            self._model.set_running(AppId(key[4:]), running=running)
        self.runningChanged.emit(key, running)

    def _save_icon(self, app: App) -> None:
        if app.executable is None:
            return
        ico = extract_icon(app.executable)
        image = _png_from_ico(ico) if ico else None
        target = icons_dir() / f"{app.id}.png"
        if image is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            # The format comes from the suffix: PySide's stubs and its binding disagree about the type of the format argument.
            image.save(str(target))
        self._model.icon_updated(app.id)
        if app_entry_path(app).exists():
            install_app_entry(app, self._launcher, target)

    # ---- properties ----

    @Property(QObject, constant=True)
    def apps(self) -> AppListModel:
        """The app list model."""
        return self._model

    def _get_settings(self) -> dict[str, str]:
        settings = self._settings
        return {
            "ravenBinary": str(settings.raven_binary),
            "prefixesRoot": str(settings.prefixes_root),
            "sourceDir": str(settings.source_dir or ""),
            "buildBox": settings.build_box,
        }

    settings = Property(dict, _get_settings, notify=settingsChanged)

    @Property(bool, notify=settingsChanged)
    def ravenFound(self) -> bool:
        """Whether the configured Raven binary exists."""
        return self._settings.raven_binary.is_file()

    # ---- apps ----

    @Slot(str, result="QVariantMap")
    def appInfo(self, app_id: str) -> dict[str, object]:
        """Return everything the app page shows about an app."""
        app = self._app(app_id)
        if app is None:
            return {}
        return {
            "appId": app.id,
            "name": app.name,
            "prefix": str(app.prefix),
            "executable": str(app.executable or ""),
            "arguments": " ".join(app.arguments),
            "desktop": app.desktop.value,
            "environment": "\n".join(f"{key}={value}" for key, value in app.environment.items()),
            "icon": self._model.icon_url(app.id),
            "inMenu": app_entry_path(app).exists(),
            "running": self._runner.running(f"app:{app.id}"),
        }

    @Slot(str, result=str)
    def createApp(self, name: str) -> str:
        """Create an app with an empty prefix and return its id, or an empty string on failure."""
        try:
            app = self._store.create(name, self._settings.prefixes_root)
        except (RavenGuiError, OSError) as error:
            self.message.emit(f"Could not create the app: {error}", True)
            return ""
        self._reload()
        return app.id

    @Slot(str, str)
    def runInstaller(self, app_id: str, installer: str) -> None:
        """Run an installer in the app's prefix, then report the programs it left behind."""
        app = self._app(app_id)
        if app is None:
            return
        path = _path(installer)
        if not path.is_file():
            self.message.emit(f"{path} does not exist.", True)
            return

        def finished(code: int, crashed: bool) -> None:  # noqa: FBT001  # the runner's callback shape
            if crashed or code:
                self.message.emit(f"The installer ended with code {code}; see the log.", True)
            self.installFinished.emit(app_id, self.findPrograms(app_id))

        self._runner.start(f"app:{app.id}", run_program(self._settings, app, path), finished)

    @Slot(str, result=list)
    def findPrograms(self, app_id: str) -> list[dict[str, object]]:
        """Return the programs in the app's prefix worth starting, shortcut targets first."""
        app = self._app(app_id)
        if app is None:
            return []
        return [
            {
                "name": program.name,
                "path": str(program.path),
                "arguments": program.arguments,
                "fromShortcut": program.from_shortcut,
            }
            for program in find_programs(app.prefix)
        ]

    @Slot(str, str, str)
    def setProgram(self, app_id: str, program: str, arguments: str) -> None:
        """Choose the program an app starts, and take its icon."""
        app = self._app(app_id)
        if app is None:
            return
        app = replace(app, executable=_path(program), arguments=tuple(arguments.split()))
        self._store.save(app)
        self._save_icon(app)
        self._reload()
        self.appChanged.emit(app_id)

    @Slot(str, str, str, str)
    def updateApp(self, app_id: str, name: str, desktop: str, environment: str) -> None:
        """Save the app page's name, display and environment fields."""
        app = self._app(app_id)
        if app is None:
            return
        variables = {}
        for line in environment.splitlines():
            key, separator, value = line.strip().partition("=")
            if line.strip() and not separator:
                self.message.emit(f"Ignored '{line.strip()}': environment lines look like NAME=value.", True)
            elif key:
                variables[key.strip()] = value.strip()
        app = replace(app, name=name.strip() or app.name, desktop=DesktopMode(desktop), environment=variables)
        self._store.save(app)
        if app_entry_path(app).exists():
            install_app_entry(app, self._launcher, icons_dir() / f"{app.id}.png")
        self._reload()
        self.appChanged.emit(app_id)

    @Slot(str)
    def runApp(self, app_id: str) -> None:
        """Start the app's program."""
        app = self._app(app_id)
        if app is None:
            return
        try:
            invocation = run_app(self._settings, app)
        except ValueError as error:
            self.message.emit(str(error), True)
            return
        if not self._runner.start(f"app:{app.id}", invocation):
            self.message.emit(f"{app.name} is already running.", False)

    @Slot(str, str)
    def runInPrefix(self, app_id: str, program: str) -> None:
        """Run another Windows program, such as an update or a tool, in the app's prefix."""
        app = self._app(app_id)
        if app is not None and not self._runner.start(
            f"app:{app.id}", run_program(self._settings, app, _path(program))
        ):
            self.message.emit(f"Something is already running in {app.name}'s prefix.", True)

    @Slot(str)
    def stop(self, key: str) -> None:
        """Stop the process under a key: an app's (app:<id>) or the rebuild."""
        self._runner.stop(key)

    @Slot(str, result=bool)
    def isRunning(self, key: str) -> bool:
        """Whether a process runs under a key."""
        return self._runner.running(key)

    @Slot(str, result=str)
    def log(self, key: str) -> str:
        """Return the kept output under a key."""
        return self._runner.log(key)

    @Slot(str)
    def clearLog(self, key: str) -> None:
        """Forget the output under a key."""
        self._runner.clear_log(key)

    @Slot(str, bool)
    def deleteApp(self, app_id: str, remove_prefix: bool) -> None:  # noqa: FBT001  # QML passes a plain boolean
        """Forget an app and, if asked, delete its prefix and snapshots."""
        app = self._app(app_id)
        if app is None:
            return
        if self._runner.running(f"app:{app.id}"):
            self.message.emit(f"Stop {app.name} before deleting it.", True)
            return
        try:
            remove_app_entry(app)
            (icons_dir() / f"{app.id}.png").unlink(missing_ok=True)
            self._store.delete(app, remove_prefix=remove_prefix)
        except OSError as error:
            self.message.emit(f"Could not delete {app.name} completely: {error}", True)
        self._reload()

    @Slot(str)
    def openPrefix(self, app_id: str) -> None:
        """Show the app's C: drive in the file manager."""
        app = self._app(app_id)
        if app is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(app.prefix / "drive_c")))

    # ---- menu entries ----

    @Slot(str, bool)
    def setInMenu(self, app_id: str, in_menu: bool) -> None:  # noqa: FBT001  # QML passes a plain boolean
        """Add the app to the application menu, or take it out."""
        app = self._app(app_id)
        if app is None:
            return
        try:
            if in_menu:
                install_app_entry(app, self._launcher, icons_dir() / f"{app.id}.png")
            else:
                remove_app_entry(app)
        except OSError as error:
            self.message.emit(f"Could not change the menu entry: {error}", True)
        self.appChanged.emit(app_id)

    @Slot()
    def installOpenWith(self) -> None:
        """Add this front end to the menu and to Open With for Windows programs."""
        try:
            path = install_front_end_entry(self._launcher)
        except OSError as error:
            self.message.emit(f"Could not write the menu entry: {error}", True)
            return
        self.message.emit(f"Added Raven to Open With ({path.name}).", False)

    # ---- snapshots ----

    @Slot(str, result=list)
    def snapshots(self, app_id: str) -> list[dict[str, str]]:
        """Return the app's snapshots, newest first."""
        app = self._app(app_id)
        if app is None:
            return []
        return [
            {
                "name": snapshot.name,
                "label": snapshot.label,
                "kind": snapshot.kind.value,
                "taken": snapshot.taken.strftime("%Y-%m-%d %H:%M:%S") if snapshot.taken else "",
            }
            for snapshot in list_snapshots(app)
        ]

    @Slot(str, str)
    def takeSnapshot(self, app_id: str, label: str) -> None:
        """Snapshot the app's prefix."""
        app = self._app(app_id)
        if app is None:
            return
        self._snapshot_operation(
            app, snapshot_command(self._settings, app, label.strip() or "manual"), "Snapshot taken."
        )

    @Slot(str, str)
    def restoreSnapshot(self, app_id: str, name: str) -> None:
        """Put the app's prefix back as a snapshot had it; Raven snapshots the current state first."""
        app = self._app(app_id)
        if app is None:
            return
        if self._runner.running(f"app:{app.id}"):
            self.message.emit(f"Stop {app.name} before restoring a snapshot.", True)
            return
        self._snapshot_operation(app, restore_command(self._settings, app, name or None), "Snapshot restored.")

    def _snapshot_operation(self, app: App, invocation: Invocation, done: str) -> None:
        key = f"snapshot:{app.id}"

        def finished(code: int, crashed: bool) -> None:  # noqa: FBT001  # the runner's callback shape
            ok = not crashed and code == 0
            if ok:
                self.message.emit(done, False)
            else:
                # Raven's one-line reason, such as "raven: no snapshot named …", is the line before the exit note.
                lines = [
                    line
                    for line in self._runner.log(key).splitlines()
                    if line.strip() and not line.startswith("[exited")
                ]
                self.message.emit(f"The snapshot operation failed: {lines[-1] if lines else f'code {code}'}", True)
            self._runner.clear_log(key)
            self.snapshotsChanged.emit(app.id)

        if not self._runner.start(key, invocation, finished):
            self.message.emit("A snapshot operation is already running for this app.", True)

    @Slot(str, str)
    def deleteSnapshot(self, app_id: str, name: str) -> None:
        """Delete one snapshot."""
        app = self._app(app_id)
        if app is None:
            return
        try:
            delete_snapshot(app, name)
        except (ValueError, OSError) as error:
            self.message.emit(f"Could not delete the snapshot: {error}", True)
        self.snapshotsChanged.emit(app_id)

    # ---- settings and Raven itself ----

    @Slot(str, str, str, str)
    def saveSettings(self, raven_binary: str, prefixes_root: str, source_dir: str, build_box: str) -> None:
        """Save the settings page."""
        self._settings = Settings(
            raven_binary=_path(raven_binary),
            prefixes_root=_path(prefixes_root),
            source_dir=_path(source_dir) if source_dir.strip() else None,
            build_box=build_box.strip(),
        )
        try:
            save_settings(self._settings)
        except OSError as error:
            self.message.emit(f"Could not save the settings: {error}", True)
            return
        self.settingsChanged.emit()
        self.message.emit("Settings saved.", False)

    @Slot()
    def rebuildRaven(self) -> None:
        """Pull Raven's sources and rebuild it."""
        try:
            invocation = rebuild_command(self._settings)
        except ValueError as error:
            self.message.emit(str(error), True)
            return

        def finished(code: int, crashed: bool) -> None:  # noqa: FBT001  # the runner's callback shape
            ok = not crashed and code == 0
            self.message.emit("Raven is rebuilt." if ok else "The rebuild failed; see the log.", not ok)
            self.settingsChanged.emit()

        self._runner.start(REBUILD_KEY, invocation, finished)

    def shutdown(self) -> None:
        """Stop everything still running."""
        self._runner.stop_all()

    @Slot(result=bool)
    def anythingRunning(self) -> bool:
        """Whether closing the window would stop a program."""
        return any(self._runner.running(f"app:{app.id}") for app in self._store.list())
