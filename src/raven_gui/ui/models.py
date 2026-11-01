"""The list of apps as a Qt model for QML."""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, QPersistentModelIndex, Qt, QUrl

from raven_gui.core.apps import App, AppId

Index = QModelIndex | QPersistentModelIndex


class Role(IntEnum):
    """The fields a delegate can read."""

    APP_ID = Qt.ItemDataRole.UserRole + 1
    NAME = Qt.ItemDataRole.UserRole + 2
    PREFIX = Qt.ItemDataRole.UserRole + 3
    EXECUTABLE = Qt.ItemDataRole.UserRole + 4
    INSTALLED = Qt.ItemDataRole.UserRole + 5
    ICON = Qt.ItemDataRole.UserRole + 6
    RUNNING = Qt.ItemDataRole.UserRole + 7


_ROLE_NAMES = {
    Role.APP_ID: b"appId",
    Role.NAME: b"name",
    Role.PREFIX: b"prefix",
    Role.EXECUTABLE: b"executable",
    Role.INSTALLED: b"installed",
    # Not "icon": delegates are buttons, whose icon property is final.
    Role.ICON: b"iconUrl",
    Role.RUNNING: b"running",
}


class AppListModel(QAbstractListModel):
    """Apps in display order, with their icon and whether they are running."""

    def __init__(self, icons_dir: Path, parent: QObject | None = None) -> None:
        """Start empty; icons are looked up in the given directory."""
        super().__init__(parent)
        self._apps: list[App] = []
        self._running: set[AppId] = set()
        self._icons_dir = icons_dir
        # Bumped whenever an icon file is rewritten, so QML does not keep showing the cached old one.
        self._icon_versions: dict[AppId, int] = {}

    def rowCount(self, parent: Index = QModelIndex()) -> int:  # noqa: B008  # Qt's own default argument
        """Return the number of apps."""
        return 0 if parent.isValid() else len(self._apps)

    def roleNames(self) -> dict[int, QByteArray]:
        """Return the names QML uses for the roles."""
        return {int(role): QByteArray(name) for role, name in _ROLE_NAMES.items()}

    def icon_url(self, app_id: AppId) -> str:
        """Return a file URL for an app's icon, or an empty string when it has none."""
        path = self._icons_dir / f"{app_id}.png"
        if not path.exists():
            return ""
        url = QUrl.fromLocalFile(str(path))
        url.setQuery(f"v={self._icon_versions.get(app_id, 0)}")
        return url.toString()

    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        """Return one field of one app."""
        if not index.isValid() or not 0 <= index.row() < len(self._apps):
            return None
        app = self._apps[index.row()]
        values: dict[int, object] = {
            Role.APP_ID: app.id,
            Role.NAME: app.name,
            Role.PREFIX: str(app.prefix),
            Role.EXECUTABLE: str(app.executable) if app.executable else "",
            Role.INSTALLED: app.installed,
            Role.ICON: self.icon_url(app.id),
            Role.RUNNING: app.id in self._running,
            Qt.ItemDataRole.DisplayRole: app.name,
        }
        return values.get(role)

    def reset(self, apps: list[App]) -> None:
        """Replace the whole list."""
        self.beginResetModel()
        self._apps = list(apps)
        self.endResetModel()

    def _row(self, app_id: AppId) -> int:
        return next((row for row, app in enumerate(self._apps) if app.id == app_id), -1)

    def _changed(self, app_id: AppId, roles: list[int]) -> None:
        row = self._row(app_id)
        if row >= 0:
            self.dataChanged.emit(self.index(row), self.index(row), roles)

    def set_running(self, app_id: AppId, *, running: bool) -> None:
        """Mark an app as running or stopped."""
        if running:
            self._running.add(app_id)
        else:
            self._running.discard(app_id)
        self._changed(app_id, [Role.RUNNING])

    def icon_updated(self, app_id: AppId) -> None:
        """Note that an app's icon file changed."""
        self._icon_versions[app_id] = self._icon_versions.get(app_id, 0) + 1
        self._changed(app_id, [Role.ICON])
