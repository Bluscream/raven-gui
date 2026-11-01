import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    required property QtObject backend
    signal openApp(string appId)
    signal installRequested(string path)
    signal settingsRequested

    title: "Apps"

    actions: [
        Kirigami.Action {
            text: "Install a program…"
            icon.name: "list-add"
            onTriggered: page.installRequested("")
        },
        Kirigami.Action {
            text: "Settings"
            icon.name: "settings-configure"
            onTriggered: page.settingsRequested()
        }
    ]

    GridView {
        id: grid

        model: page.backend.apps
        cellWidth: Kirigami.Units.gridUnit * 10
        cellHeight: Kirigami.Units.gridUnit * 10
        topMargin: Kirigami.Units.largeSpacing
        leftMargin: Kirigami.Units.largeSpacing

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: grid.count === 0
            icon.name: "wine"
            text: "No apps yet"
            explanation: "Pick a Windows installer or program. Raven gives each app its own C: drive."
            helpfulAction: Kirigami.Action {
                text: "Install a program…"
                icon.name: "list-add"
                onTriggered: page.installRequested("")
            }
        }

        delegate: Controls.ItemDelegate {
            id: tile

            required property string appId
            required property string name
            required property string iconUrl
            required property bool installed
            required property bool running

            width: grid.cellWidth - Kirigami.Units.largeSpacing
            height: grid.cellHeight - Kirigami.Units.largeSpacing
            onClicked: page.openApp(appId)
            onDoubleClicked: if (installed) page.backend.runApp(appId)

            Controls.ToolTip.text: installed ? "Double-click to start" : "No program chosen yet"
            Controls.ToolTip.visible: hovered
            Controls.ToolTip.delay: Kirigami.Units.toolTipDelay

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: Kirigami.Units.iconSizes.huge
                    Layout.preferredHeight: Kirigami.Units.iconSizes.huge
                    source: tile.iconUrl !== "" ? tile.iconUrl : "application-x-ms-dos-executable"
                    opacity: tile.installed ? 1 : 0.5

                    Rectangle {
                        visible: tile.running
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        width: Kirigami.Units.gridUnit * 0.8
                        height: width
                        radius: width / 2
                        color: Kirigami.Theme.positiveTextColor
                        border.color: Kirigami.Theme.backgroundColor
                        border.width: 2
                    }
                }
                Controls.Label {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: tile.name
                    elide: Text.ElideRight
                    maximumLineCount: 2
                    wrapMode: Text.Wrap
                }
                Controls.Button {
                    Layout.alignment: Qt.AlignHCenter
                    visible: tile.installed
                    icon.name: tile.running ? "media-playback-stop" : "media-playback-start"
                    text: tile.running ? "Stop" : "Play"
                    onClicked: tile.running ? page.backend.stop("app:" + tile.appId) : page.backend.runApp(tile.appId)
                }
            }
        }
    }
}
