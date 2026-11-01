import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

// After an installer: which of the programs it left in the prefix the app should start.
Kirigami.Dialog {
    id: dialog

    required property QtObject backend
    property string appId: ""
    property var programs: []

    title: "Choose the program to start"
    preferredWidth: Kirigami.Units.gridUnit * 30
    preferredHeight: Kirigami.Units.gridUnit * 24
    standardButtons: Kirigami.Dialog.NoButton

    function openFor(appId, programs) {
        dialog.appId = appId;
        dialog.programs = programs;
        list.currentIndex = programs.length > 0 ? 0 : -1;
        open();
    }

    customFooterActions: [
        Kirigami.Action {
            text: "Use this program"
            icon.name: "dialog-ok-apply"
            enabled: list.currentIndex >= 0
            onTriggered: {
                const program = dialog.programs[list.currentIndex];
                dialog.backend.setProgram(dialog.appId, program.path, program.arguments);
                dialog.close();
            }
        },
        Kirigami.Action {
            text: "Decide later"
            icon.name: "dialog-cancel"
            onTriggered: dialog.close()
        }
    ]

    ListView {
        id: list

        implicitHeight: Kirigami.Units.gridUnit * 18
        clip: true
        model: dialog.programs

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 2
            visible: list.count === 0
            icon.name: "dialog-warning"
            text: "No programs found"
            explanation: "The installer may have failed or been cancelled; its log is on the app page. You can also pick a program there by hand."
        }

        delegate: Controls.ItemDelegate {
            required property var modelData
            required property int index

            width: ListView.view.width
            highlighted: ListView.isCurrentItem
            onClicked: list.currentIndex = index

            contentItem: ColumnLayout {
                spacing: 0
                RowLayout {
                    Controls.Label {
                        text: modelData.name
                        font.bold: modelData.fromShortcut
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Kirigami.Chip {
                        visible: modelData.fromShortcut
                        text: "Shortcut"
                        closable: false
                        checkable: false
                    }
                }
                Controls.Label {
                    text: modelData.path
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
            }
        }
    }
}
