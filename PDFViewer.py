from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, QSize, QRectF, QThread, pyqtSignal, QCoreApplication
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtSvg import QSvgGenerator
from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QWidget,
    QVBoxLayout,
)
import os, shutil
from utils import filter_pdf

class PdfLoaderThread(QThread):
    loaded = pyqtSignal(object, int)  # (QPdfDocument or None, index)

    def __init__(self, path, index, parent=None):
        super().__init__(parent)
        self.path = path
        self.index = index

    def run(self):
        doc = QPdfDocument(None)
        err = doc.load(self.path)
        if err != QPdfDocument.Error.None_:
            # emit None on error
            self.loaded.emit(None, self.index)
        else:
            # move the doc into the GUI thread
            doc.moveToThread(QCoreApplication.instance().thread())
            self.loaded.emit(doc, self.index)


class PdfView(QPdfView):
    def __init__(self, parent=None):
        super().__init__(parent)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # manual zoom mode
            if self.zoomMode() != QPdfView.ZoomMode.Custom:
                self.setZoomMode(QPdfView.ZoomMode.Custom)
            # zoom in/out
            delta = event.angleDelta().y()
            factor = 1.25 if delta > 0 else 0.8
            self.setZoomFactor(self.zoomFactor() * factor)
            event.accept()
        else:
            super().wheelEvent(event)


class PdfViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentPdf = None
        self.doc = None
        self.loader = None
        self.file_list = []
        self.current_index = -1

        self.view = PdfView(self)
        self.view.setDocument(self.doc)
        # single page mode only 
        self.view.setPageMode(QPdfView.PageMode.SinglePage)
        # fit to view on load
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def _start_loading(self, path, index):
        # disable view during load
        self.view.setEnabled(False)
        # kill old loader
        if self.loader:
            self.loader.loaded.disconnect(self._on_loaded)
            self.loader.quit()
            self.loader.wait()
        self.loader = PdfLoaderThread(path, index)
        self.loader.loaded.connect(self._on_loaded)
        self.loader.start()

    def _on_loaded(self, new_doc, index):
        if new_doc is None:
            QMessageBox.warning(self, "Error", f"Failed to load:\n{self.file_list[index]}")
            return
        # save current PDF
        self.currentPdf = self.file_list[index]
        # remove old doc from the view 
        if self.doc:
            self.view.setDocument(None)
            # schedule to del the old one
            self.doc.deleteLater()

        # setup new doc
        self.doc = new_doc
        self.view.setDocument(self.doc)

        # re-apply our single-page + fit-width rules
        self.view.setPageMode(QPdfView.PageMode.SinglePage)       
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)       
        self.view.setEnabled(True)
    
    def _load_folder(self, folder):
        pdfs = sorted(
            os.path.join(folder, fn)
            for fn in os.listdir(folder)
            if fn.lower().endswith(".pdf")
        )
        if not pdfs:
            QMessageBox.warning(self, "No PDFs", "Folder contains no PDF files.")
            return
        self.file_list = filter_pdf(pdf_files=pdfs)
        self.current_index = 0
        self._start_loading(self.file_list[0], 0)

    def _load_file(self, path: str):
        if not os.path.isfile(path) or not path.lower().endswith(".pdf"):
            QMessageBox.warning(self, "Invalid PDF", f"Not a PDF:\n{path}")
            return
        self.currentPdf = path
        self.file_list = [path]
        self.current_index = 0
        self._start_loading(path, 0)
    
    def next_file(self):
        if self.current_index < len(self.file_list) - 1:
            self.current_index += 1
            self._start_loading(self.file_list[self.current_index], self.current_index)

    def prev_file(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._start_loading(self.file_list[self.current_index], self.current_index)

    def zoom_in(self):
        if self.view.zoomMode() != QPdfView.ZoomMode.Custom:
            self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(self.view.zoomFactor() * 1.25)

    def zoom_out(self):
        if self.view.zoomMode() != QPdfView.ZoomMode.Custom:
            self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(self.view.zoomFactor() * 0.8)

    def save_as(self):
        if not self.currentPdf or self.doc.pageCount() == 0:
            return
        
        # set default name for saved file
        base_name = os.path.splitext(os.path.basename(self.currentPdf))[0]
        # default_dir  = os.path.dirname(self.currentPdf)
        # dialog start in the current directory
        default_path = os.path.join(os.getcwd(), base_name)

        if not self.currentPdf or self.doc.pageCount() == 0:
            return
        path, filt = QFileDialog.getSaveFileName(
            self, "Save As", default_path, "PNG Image (*.png);;SVG Vector (*.svg);;PDF Document (*.pdf)"
        )
        if not path:
            return

        base, ext = os.path.splitext(path)
        ext = ext.lower()
        if ext not in (".png", ".svg", ".pdf"):
            if "PNG" in filt:
                ext = ".png"
            elif "SVG" in filt:
                ext = ".svg"
            elif "PDF" in filt:
                ext = ".pdf"
            else:
                QMessageBox.warning(self, "Save As", "Unknown file type.")
                return
            path = base + ext

        page = self.view.pageNavigator().currentPage()

        # get page size (in points)
        page_pts = self.doc.pagePointSize(page)  
        # calculate pixel resolution based on scale factor
        if self.view.zoomMode() == QPdfView.ZoomMode.Custom: # user in zoom mode -> use that zoom factor
            scale = self.view.zoomFactor()
        else: # if not -> use target_dpi at 72 dpi (default in QtPdf) -> higher dpi for higher exportation quality
            scale = 1.0 # (target_dpi/72 = 72/72)
        px_w = int(page_pts.width()  * scale)
        px_h = int(page_pts.height() * scale)
        
        if ext == ".png":
            img = self.doc.render(page, QSize(px_w, px_h))
            if img.isNull():
                QMessageBox.warning(self, "Save As", "Failed to render PNG.")
            else:
                img.save(path, "PNG")
        elif ext == ".svg":
            img = self.doc.render(page, QSize(px_w, px_h))
            if not img.isNull():
                gen = QSvgGenerator()
                gen.setFileName(path)
                gen.setSize(QSize(px_w, px_h))
                gen.setViewBox(QRectF(0, 0, px_w, px_h))
                gen.setTitle(os.path.basename(path))
                painter = QPainter(gen)
                painter.drawImage(0, 0, img)
                painter.end()
        else:  # .pdf -> copy original
            try:
                shutil.copy(self.currentPdf, path)
            except Exception as e:
                QMessageBox.warning(self, "Save As", f"Copy failed: {e}")
