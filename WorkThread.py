from PyQt6.QtCore import QThread, pyqtSignal

class Worker(QThread):
    # Signal emitted when work is done, carrying result
    finished = pyqtSignal(object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        # Call the long‐running function
        result = self.fn(*self.args, **self.kwargs)
        # Emit the result
        self.finished.emit(result)

