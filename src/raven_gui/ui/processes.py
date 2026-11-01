"""Running Raven processes under Qt and collecting what they print, one log per key."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from raven_gui.core.command import Invocation

logger = logging.getLogger(__name__)

# Lines kept per log; Raven's traces can run to millions of lines and the view only needs the recent ones.
LOG_LINES = 5000

Finished = Callable[[int, bool], None]


class ProcessRunner(QObject):
    """Starts processes by key, keeps their output, and reports when they start and end."""

    # key, text appended
    output = Signal(str, str)
    # key, running
    stateChanged = Signal(str, bool)

    def __init__(self, parent: QObject | None = None) -> None:
        """Start with no processes and no logs."""
        super().__init__(parent)
        self._processes: dict[str, QProcess] = {}
        self._logs: dict[str, deque[str]] = {}

    def running(self, key: str) -> bool:
        """Whether the process under a key is running."""
        return key in self._processes

    def log(self, key: str) -> str:
        """Return the kept output of a key."""
        return "".join(self._logs.get(key, ()))

    def clear_log(self, key: str) -> None:
        """Forget a key's output."""
        self._logs.pop(key, None)

    def _append(self, key: str, text: str) -> None:
        if not text:
            return
        self._logs.setdefault(key, deque(maxlen=LOG_LINES)).extend(text.splitlines(keepends=True))
        self.output.emit(key, text)

    def start(self, key: str, invocation: Invocation, on_finished: Finished | None = None) -> bool:
        """Start a process under a key; returns False when one is already running there."""
        if key in self._processes:
            return False
        process = QProcess(self)
        environment = QProcessEnvironment.systemEnvironment()
        for name, value in invocation.environment.items():
            environment.insert(name, value)
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(invocation.cwd))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(
            lambda: self._append(key, bytes(process.readAllStandardOutput().data()).decode("utf-8", "replace"))
        )

        def finished(code: int, status: QProcess.ExitStatus) -> None:
            crashed = status is QProcess.ExitStatus.CrashExit
            self._append(key, f"\n[exited with code {code}{' after a crash or a stop' if crashed else ''}]\n")
            self._processes.pop(key, None)
            process.deleteLater()
            self.stateChanged.emit(key, False)
            if on_finished:
                on_finished(code, crashed)

        def failed(error: QProcess.ProcessError) -> None:
            # A program that never started gets no finished signal; one that crashed gets both, and finished cleans up.
            if error is QProcess.ProcessError.FailedToStart:
                self._append(key, f"\n[could not start {invocation.argv[0]}: {process.errorString()}]\n")
                self._processes.pop(key, None)
                process.deleteLater()
                self.stateChanged.emit(key, False)
                if on_finished:
                    on_finished(-1, True)

        process.finished.connect(finished)
        process.errorOccurred.connect(failed)
        self._processes[key] = process
        self._append(key, f"$ {' '.join(invocation.argv)}\n")
        logger.info("Starting %s: %s", key, invocation.argv)
        process.start(invocation.argv[0], list(invocation.argv[1:]))
        self.stateChanged.emit(key, True)
        return True

    def stop(self, key: str) -> None:
        """Ask a process to end, and kill it if it has not after a few seconds."""
        process = self._processes.get(key)
        if process is None:
            return
        process.terminate()
        if not process.waitForFinished(5000):
            process.kill()

    def stop_all(self) -> None:
        """Stop every process, for when the window closes."""
        for key in list(self._processes):
            self.stop(key)
