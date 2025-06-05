import os
import time
from PyQt6.QtCore import QThread, pyqtSignal

class LogFileWatcher(QThread):
    logfile_found = pyqtSignal(str)

    def __init__(self, folder, pattern="*.log", poll_interval=2, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.pattern = pattern
        self.poll_interval = poll_interval
        self._running = True

    def run(self):
        while self._running:
            files = [f for f in os.listdir(self.folder) if f.endswith(".log")]
            if files:
                files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(self.folder, f)), reverse=True)
                latest = os.path.join(self.folder, files[0])
                print(latest)
                self.logfile_found.emit(latest)
                break  # stop after found

    def stop(self):
        self._running = False
        self.wait()