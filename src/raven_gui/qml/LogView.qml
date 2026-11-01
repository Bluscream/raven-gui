import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

// The output of the process under one key, following new lines as they arrive.
ColumnLayout {
    id: view

    required property QtObject backend
    required property string key

    spacing: Kirigami.Units.smallSpacing

    function reload() {
        area.text = backend.log(key);
        area.cursorPosition = area.length;
    }

    onKeyChanged: reload()
    Component.onCompleted: reload()

    Connections {
        target: view.backend
        function onLogAppended(key, text) {
            if (key !== view.key)
                return;
            // Appending keeps the view responsive; the backend keeps the bounded copy reload() reads.
            area.insert(area.length, text);
            if (follow.checked)
                area.cursorPosition = area.length;
        }
    }

    RowLayout {
        Controls.CheckBox {
            id: follow
            text: "Follow"
            checked: true
        }
        Item {
            Layout.fillWidth: true
        }
        Controls.Button {
            icon.name: "edit-copy"
            text: "Copy"
            onClicked: {
                area.selectAll();
                area.copy();
                area.deselect();
            }
        }
        Controls.Button {
            icon.name: "edit-clear-history"
            text: "Clear"
            onClicked: {
                view.backend.clearLog(view.key);
                area.text = "";
            }
        }
    }

    Controls.ScrollView {
        Layout.fillWidth: true
        Layout.preferredHeight: Kirigami.Units.gridUnit * 16

        Controls.TextArea {
            id: area
            readOnly: true
            wrapMode: Text.WrapAnywhere
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            placeholderText: "Nothing has run yet."
        }
    }
}
