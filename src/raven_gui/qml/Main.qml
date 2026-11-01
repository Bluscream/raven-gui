import QtQuick
import QtQuick.Controls as Controls
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    required property QtObject backend
    // A Windows program handed over by the file manager, to install or run.
    required property string openFile

    title: "Raven"
    width: Kirigami.Units.gridUnit * 56
    height: Kirigami.Units.gridUnit * 38
    minimumWidth: Kirigami.Units.gridUnit * 24
    minimumHeight: Kirigami.Units.gridUnit * 20

    pageStack.initialPage: AppsPage {
        backend: root.backend
        onOpenApp: appId => root.showApp(appId)
        onInstallRequested: path => installDialog.openFor(path)
        onSettingsRequested: root.pageStack.layers.push(settingsPage)
    }
    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.ToolBar

    function showApp(appId) {
        while (pageStack.depth > 1)
            pageStack.pop();
        pageStack.push(appPageComponent, { appId: appId });
    }

    Component {
        id: appPageComponent
        AppPage {
            backend: root.backend
            onDeleted: root.pageStack.pop()
        }
    }

    Component {
        id: settingsPage
        SettingsPage {
            backend: root.backend
        }
    }

    InstallDialog {
        id: installDialog
        backend: root.backend
        onStarted: appId => root.showApp(appId)
    }

    ChooseProgramDialog {
        id: chooseDialog
        backend: root.backend
    }

    Connections {
        target: root.backend
        function onMessage(text, isError) {
            root.showPassiveNotification(text, isError ? "long" : "short");
        }
        function onInstallFinished(appId, programs) {
            chooseDialog.openFor(appId, programs);
        }
    }

    Controls.Dialog {
        id: quitDialog
        anchors.centerIn: parent
        modal: true
        title: "Programs are still running"
        standardButtons: Controls.Dialog.Ok | Controls.Dialog.Cancel
        Controls.Label {
            text: "Closing Raven stops the Windows programs it started. Close anyway?"
            wrapMode: Text.WordWrap
        }
        onAccepted: {
            root.closeConfirmed = true;
            root.close();
        }
    }

    property bool closeConfirmed: false
    onClosing: close => {
        if (!closeConfirmed && backend.anythingRunning()) {
            close.accepted = false;
            quitDialog.open();
        }
    }

    Component.onCompleted: {
        if (!backend.ravenFound)
            showPassiveNotification("Raven was not found at " + backend.settings.ravenBinary + ". Set its path in the settings.", "long");
        if (openFile !== "")
            installDialog.openFor(openFile);
    }
}
