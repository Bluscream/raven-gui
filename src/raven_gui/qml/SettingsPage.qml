import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kirigamiaddons.formcard as FormCard

FormCard.FormCardPage {
    id: page

    required property QtObject backend
    property bool rebuilding: backend.isRunning("rebuild")

    title: "Settings"

    function save() {
        backend.saveSettings(ravenField.text, prefixesField.text, sourceField.text, boxField.text);
    }

    Connections {
        target: page.backend
        function onRunningChanged(key, running) {
            if (key === "rebuild")
                page.rebuilding = running;
        }
    }

    FormCard.FormHeader {
        title: "Raven"
    }
    FormCard.FormCard {
        FormCard.FormTextFieldDelegate {
            id: ravenField
            label: "Raven program"
            text: page.backend.settings.ravenBinary
            onEditingFinished: page.save()
        }
        FormCard.FormTextDelegate {
            text: page.backend.ravenFound ? "Found" : "Not found"
            icon.name: page.backend.ravenFound ? "emblem-success" : "emblem-error"
            description: page.backend.ravenFound ? "" : "Build Raven from source and point this at build/native/raven."
        }
        FormCard.FormDelegateSeparator {}
        FormCard.FormTextFieldDelegate {
            id: prefixesField
            label: "New prefixes go in"
            text: page.backend.settings.prefixesRoot
            onEditingFinished: page.save()
        }
    }

    FormCard.FormHeader {
        title: "Desktop"
    }
    FormCard.FormCard {
        FormCard.FormButtonDelegate {
            text: "Add Raven to the menu and to Open With"
            description: "Lets the file manager open .exe and .msi files here."
            icon.name: "document-open"
            onClicked: page.backend.installOpenWith()
        }
    }

    FormCard.FormHeader {
        title: "Updating Raven"
    }
    FormCard.FormCard {
        FormCard.FormTextFieldDelegate {
            id: sourceField
            label: "Source directory"
            placeholderText: "The git checkout Raven was built from"
            text: page.backend.settings.sourceDir
            onEditingFinished: page.save()
        }
        FormCard.FormDelegateSeparator {}
        FormCard.FormTextFieldDelegate {
            id: boxField
            label: "Build container (distrobox)"
            placeholderText: "Leave empty to build on this system"
            text: page.backend.settings.buildBox
            onEditingFinished: page.save()
        }
        FormCard.FormDelegateSeparator {}
        FormCard.FormButtonDelegate {
            text: page.rebuilding ? "Stop the rebuild" : "Pull and rebuild Raven"
            description: "Runs git pull and the build. The provisioned components are not refreshed."
            icon.name: page.rebuilding ? "process-stop" : "run-build"
            enabled: page.rebuilding || sourceField.text !== ""
            onClicked: page.rebuilding ? page.backend.stop("rebuild") : page.backend.rebuildRaven()
        }
        FormCard.AbstractFormDelegate {
            background: null
            contentItem: LogView {
                backend: page.backend
                key: "rebuild"
            }
        }
    }
}
