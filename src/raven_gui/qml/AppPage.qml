import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kirigamiaddons.formcard as FormCard

FormCard.FormCardPage {
    id: page

    required property QtObject backend
    property string appId: ""
    property var info: ({})
    property var snapshots: []
    property bool running: false
    signal deleted

    title: info.name ?? ""

    function reload() {
        info = backend.appInfo(appId);
        snapshots = backend.snapshots(appId);
        running = backend.isRunning("app:" + appId);
        nameField.text = info.name ?? "";
        argumentsField.text = info.arguments ?? "";
        environmentField.text = info.environment ?? "";
        desktopBox.currentIndex = Math.max(0, desktopBox.model.indexOf(info.desktop ?? "wayland"));
    }

    function save() {
        backend.updateApp(appId, nameField.text, desktopBox.currentValue, environmentField.text);
    }

    onAppIdChanged: reload()

    Connections {
        target: page.backend
        function onAppChanged(appId) {
            if (appId === page.appId)
                page.reload();
        }
        function onSnapshotsChanged(appId) {
            if (appId === page.appId)
                page.snapshots = page.backend.snapshots(appId);
        }
        function onRunningChanged(key, running) {
            if (key === "app:" + page.appId)
                page.running = running;
        }
    }

    actions: [
        Kirigami.Action {
            text: page.running ? "Stop" : "Play"
            icon.name: page.running ? "media-playback-stop" : "media-playback-start"
            enabled: page.running || page.info.executable !== ""
            onTriggered: page.running ? page.backend.stop("app:" + page.appId) : page.backend.runApp(page.appId)
        },
        Kirigami.Action {
            text: "Run another program here…"
            icon.name: "system-run"
            enabled: !page.running
            onTriggered: {
                exeDialog.forRunning = true;
                exeDialog.open();
            }
        },
        Kirigami.Action {
            text: "Open C: drive"
            icon.name: "folder-open"
            onTriggered: page.backend.openPrefix(page.appId)
        },
        Kirigami.Action {
            text: "Delete…"
            icon.name: "edit-delete"
            onTriggered: deleteDialog.open()
        }
    ]

    FileDialog {
        id: exeDialog
        property bool forRunning: false
        title: forRunning ? "Run a program in this prefix" : "Choose the program to start"
        nameFilters: ["Windows programs (*.exe *.EXE *.msi *.MSI)", "All files (*)"]
        currentFolder: "file://" + (page.info.prefix ?? "") + "/drive_c"
        onAccepted: {
            const path = decodeURIComponent(selectedFile.toString().replace(/^file:\/\//, ""));
            if (forRunning)
                page.backend.runInPrefix(page.appId, path);
            else
                page.backend.setProgram(page.appId, path, argumentsField.text);
        }
    }

    Kirigami.PromptDialog {
        id: deleteDialog
        title: "Delete " + (page.info.name ?? "")
        subtitle: "Removes the app from this list and from the menu."
        standardButtons: Kirigami.Dialog.NoButton
        customFooterActions: [
            Kirigami.Action {
                text: "Delete app and its prefix"
                icon.name: "edit-delete"
                onTriggered: {
                    page.backend.deleteApp(page.appId, true);
                    deleteDialog.close();
                    page.deleted();
                }
            },
            Kirigami.Action {
                text: "Keep the prefix"
                icon.name: "edit-delete-shred"
                onTriggered: {
                    page.backend.deleteApp(page.appId, false);
                    deleteDialog.close();
                    page.deleted();
                }
            },
            Kirigami.Action {
                text: "Cancel"
                icon.name: "dialog-cancel"
                onTriggered: deleteDialog.close()
            }
        ]
    }

    Kirigami.PromptDialog {
        id: snapshotDialog
        title: "Take a snapshot"
        standardButtons: Kirigami.Dialog.Ok | Kirigami.Dialog.Cancel
        onAccepted: page.backend.takeSnapshot(page.appId, labelField.text)
        Controls.TextField {
            id: labelField
            placeholderText: "Label, such as before-update"
        }
    }

    Kirigami.PromptDialog {
        id: restoreDialog
        property string snapshot: ""
        title: "Restore this snapshot?"
        subtitle: "The prefix goes back to how it was then. Raven snapshots its current state first, so this can be undone."
        standardButtons: Kirigami.Dialog.Ok | Kirigami.Dialog.Cancel
        onAccepted: page.backend.restoreSnapshot(page.appId, snapshot)
    }

    // ---- header ----
    FormCard.FormCard {
        Layout.topMargin: Kirigami.Units.largeSpacing
        FormCard.AbstractFormDelegate {
            background: null
            contentItem: RowLayout {
                spacing: Kirigami.Units.largeSpacing
                Kirigami.Icon {
                    source: page.info.icon ? page.info.icon : "application-x-ms-dos-executable"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.huge
                    Layout.preferredHeight: Kirigami.Units.iconSizes.huge
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Kirigami.Heading {
                        text: page.info.name ?? ""
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Controls.Label {
                        text: page.running ? "Running" : (page.info.executable ? "Ready" : "No program chosen yet")
                        color: page.running ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.disabledTextColor
                    }
                }
            }
        }
    }

    // ---- program ----
    FormCard.FormHeader {
        title: "Program"
    }
    FormCard.FormCard {
        FormCard.FormTextDelegate {
            text: "Starts"
            description: page.info.executable ? page.info.executable : "Nothing chosen yet"
        }
        FormCard.FormDelegateSeparator {}
        FormCard.FormButtonDelegate {
            text: "Find installed programs…"
            icon.name: "search"
            onClicked: page.backend.installFinished(page.appId, page.backend.findPrograms(page.appId))
        }
        FormCard.FormButtonDelegate {
            text: "Choose a program file…"
            icon.name: "document-open"
            onClicked: {
                exeDialog.forRunning = false;
                exeDialog.open();
            }
        }
        FormCard.FormDelegateSeparator {}
        FormCard.FormTextFieldDelegate {
            id: argumentsField
            label: "Arguments"
            placeholderText: "Passed to the program, separated by spaces"
            onEditingFinished: if (page.info.executable) page.backend.setProgram(page.appId, page.info.executable, text)
        }
        FormCard.FormSwitchDelegate {
            text: "Show in the application menu"
            description: "Starts the app straight from the launcher, without this window."
            checked: page.info.inMenu ?? false
            enabled: page.info.executable !== ""
            onToggled: page.backend.setInMenu(page.appId, checked)
        }
    }

    // ---- settings ----
    FormCard.FormHeader {
        title: "Settings"
    }
    FormCard.FormCard {
        FormCard.FormTextFieldDelegate {
            id: nameField
            label: "Name"
            onEditingFinished: page.save()
        }
        FormCard.FormDelegateSeparator {}
        FormCard.FormComboBoxDelegate {
            id: desktopBox
            text: "Windows shown on"
            description: "X11 is experimental in Raven. None suits console programs."
            model: ["wayland", "x11", "none"]
            onActivated: page.save()
        }
        FormCard.FormDelegateSeparator {}
        FormCard.FormTextAreaDelegate {
            id: environmentField
            label: "Environment variables"
            placeholderText: "One NAME=value per line, such as RAVEN_THEME=classic"
            onEditingFinished: page.save()
        }
        FormCard.FormTextDelegate {
            text: "Prefix"
            description: page.info.prefix ?? ""
        }
    }

    // ---- snapshots ----
    FormCard.FormHeader {
        title: "Snapshots"
    }
    FormCard.FormCard {
        FormCard.FormButtonDelegate {
            text: "Take a snapshot…"
            icon.name: "camera-photo"
            onClicked: {
                labelField.text = "";
                snapshotDialog.open();
            }
        }
        FormCard.FormTextDelegate {
            visible: page.snapshots.length === 0
            text: "No snapshots yet"
            description: "Raven takes one on its own before a recognised installer runs."
        }
        Repeater {
            model: page.snapshots
            delegate: FormCard.AbstractFormDelegate {
                id: row
                required property var modelData
                Layout.fillWidth: true
                background: null
                contentItem: RowLayout {
                    Kirigami.Icon {
                        source: row.modelData.kind === "install" ? "run-install" : row.modelData.kind === "before-restore" ? "edit-undo" : "camera-photo"
                        Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                        Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Controls.Label {
                            text: row.modelData.label
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Controls.Label {
                            text: row.modelData.taken
                            font: Kirigami.Theme.smallFont
                            color: Kirigami.Theme.disabledTextColor
                        }
                    }
                    Controls.Button {
                        icon.name: "edit-undo"
                        text: "Restore"
                        enabled: !page.running
                        onClicked: {
                            restoreDialog.snapshot = row.modelData.name;
                            restoreDialog.open();
                        }
                    }
                    Controls.Button {
                        icon.name: "edit-delete"
                        display: Controls.AbstractButton.IconOnly
                        text: "Delete snapshot"
                        Controls.ToolTip.text: text
                        Controls.ToolTip.visible: hovered
                        onClicked: page.backend.deleteSnapshot(page.appId, row.modelData.name)
                    }
                }
            }
        }
    }

    // ---- log ----
    FormCard.FormHeader {
        title: "Log"
    }
    FormCard.FormCard {
        FormCard.AbstractFormDelegate {
            background: null
            contentItem: LogView {
                backend: page.backend
                key: "app:" + page.appId
            }
        }
    }
}
