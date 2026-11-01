import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialog

    required property QtObject backend
    signal started(string appId)

    title: "Install a program"
    padding: Kirigami.Units.largeSpacing
    preferredWidth: Kirigami.Units.gridUnit * 28
    standardButtons: Kirigami.Dialog.NoButton

    function openFor(path) {
        fileField.text = path;
        nameField.text = path === "" ? "" : guessName(path);
        installerChoice.checked = true;
        open();
        nameField.forceActiveFocus();
    }

    // "Some App Setup 1.2.exe" reads best as "Some App".
    function guessName(path) {
        let base = path.split("/").pop().replace(/\.(exe|msi)$/i, "");
        base = base.replace(/[-_ .]*(setup|install(er)?|x64|x86|win(32|64)?|v?\d[\d.]*)\b.*$/i, "");
        return base.replace(/[-_]+/g, " ").trim() || path.split("/").pop();
    }

    customFooterActions: [
        Kirigami.Action {
            text: installerChoice.checked ? "Install" : "Add"
            icon.name: installerChoice.checked ? "run-install" : "list-add"
            enabled: nameField.text.trim() !== "" && fileField.text !== ""
            onTriggered: {
                const appId = dialog.backend.createApp(nameField.text);
                if (appId === "")
                    return;
                if (installerChoice.checked)
                    dialog.backend.runInstaller(appId, fileField.text);
                else
                    dialog.backend.setProgram(appId, fileField.text, "");
                dialog.close();
                dialog.started(appId);
            }
        },
        Kirigami.Action {
            text: "Cancel"
            icon.name: "dialog-cancel"
            onTriggered: dialog.close()
        }
    ]

    FileDialog {
        id: fileDialog
        title: "Choose a Windows program"
        nameFilters: ["Windows programs and installers (*.exe *.EXE *.msi *.MSI)", "All files (*)"]
        onAccepted: {
            fileField.text = decodeURIComponent(selectedFile.toString().replace(/^file:\/\//, ""));
            if (nameField.text.trim() === "")
                nameField.text = dialog.guessName(fileField.text);
        }
    }

    Kirigami.FormLayout {
        RowLayout {
            Kirigami.FormData.label: "Program:"
            Controls.TextField {
                id: fileField
                Layout.fillWidth: true
                placeholderText: "setup.exe, an .msi or a portable program"
            }
            Controls.Button {
                icon.name: "document-open"
                text: "Browse…"
                onClicked: fileDialog.open()
            }
        }
        Controls.TextField {
            id: nameField
            Kirigami.FormData.label: "Name:"
            placeholderText: "What to call the app"
        }
        Controls.RadioButton {
            id: installerChoice
            Kirigami.FormData.label: "This is:"
            text: "An installer: run it in a new prefix"
            checked: true
        }
        Controls.RadioButton {
            text: "A portable program: run it from where it is"
        }
        Controls.Label {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
            wrapMode: Text.WordWrap
            font: Kirigami.Theme.smallFont
            color: Kirigami.Theme.disabledTextColor
            text: installerChoice.checked
                ? "When the installer closes, Raven lists the programs it installed so you can pick the one to start. Raven snapshots the prefix before a recognised installer runs."
                : "The program gets its own prefix for its settings and registry, but stays in its folder."
        }
    }
}
