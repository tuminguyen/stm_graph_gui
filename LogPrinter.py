import time
from PyQt6.QtCore import QThread, pyqtSignal

class LogPrinter(QThread):
    newLine = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self._running = True

    def run(self):
        try:
            with open(self.path, "r") as f:
                # print every line already in file
                for line in f:
                    if not self._running:
                        return
                    self.newLine.emit(line.rstrip("\n"))

                # tail file -- read new lines as they arrive
                while self._running:
                    line = f.readline()
                    if line:
                        self.newLine.emit(line.rstrip("\n"))
                    else:
                        time.sleep(0.2)
        except Exception as e:
            self.newLine.emit(f"[Error tailing file: {e}]")

    def stop(self):
        self._running = False
        self.wait()