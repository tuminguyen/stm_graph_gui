import sys, os, re


gui_path = "gui.ui"
if getattr(sys, 'frozen', False):
    os.environ['GDAL_DATA'] = os.path.join(sys._MEIPASS, 'gdal_data')
    gui_path = os.path.join(sys._MEIPASS, "gui.ui")
    
    
import stm_graph
import torch
import time
import pandas as pd
from PyQt6.uic import loadUi
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QMovie
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
    QTableWidgetItem,
    QMainWindow,
    QCheckBox,
    QPushButton,
    QLabel,
    QLineEdit, 
    QComboBox,
    QAbstractItemView
)
from WorkThread import Worker
from PDFViewer import PdfViewerWidget
from LogPrinter import LogPrinter as LP
from LogFileWatcher import LogFileWatcher as LFW
from thread_func import *
from config import CONFIG

crs_pattern = r"(?i)^EPSG:\d{3,}$"


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return relative_path


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi(gui_path, self)
        self.setWindowTitle("STM-Graph v1.0.0")
        self.setWindowIcon(QIcon(resource_path("images/app-icon.png")))
        self.setFixedSize(self.geometry().width(), self.geometry().height())
        self.init_ui()

        # initial value -- DATA
        self.loaded_data = None
        self.data_tab_index = 0
        self.model_tab_index = 0
        self.column_names = []
        self.filter_start_date = None
        self.filter_end_date = None
        self.osm_extracted_features = None
        self.data_int_line_edits = {
            'horizon': self.lineHorizon,
            'windowSize': self.lineWindowSize,
            'interStep': self.lineInterStep,
        }
        self.bounds_line_edits = {
            'minLon': self.lineMinLong,
            'minLat': self.lineMinLat,
            'maxLon': self.lineMaxLong,
            'maxLat': self.lineMaxLat,
        }
        self.lineGridSizeVal.setText("20000")
        self.lineVoronoiCellSmallVal.setText("20000")
        self.lineVoronoiCellLargeVal.setText("30000")
        # func connect -- DATA
        for le in self.data_int_line_edits.values():
            le.textChanged.connect(self.validate_data_s2) 
        for le in self.bounds_line_edits.values():
            le.textChanged.connect(self.validate_data_s2)
        self.comboBoxOutType.activated.connect(self.validate_data_s2)
        self.comboBoxTestMode.currentTextChanged.connect(self.validate_data_s2)
        self.comboBoxFilterDS.activated.connect(self.validate_data_s2)
        self.comboBoxFilterDE.activated.connect(self.validate_data_s2)
        self.dateEditStart.dateChanged.connect(self.validate_data_s2)
        self.dateEditEnd.dateChanged.connect(self.validate_data_s2)
        self.comboBoxUKG.activated.connect(self.validate_data_s2)
        self.checkOSMPoi.stateChanged.connect(self.validate_data_s2)
        self.checkOSMRoad.stateChanged.connect(self.validate_data_s2)
        self.checkOSMJunction.stateChanged.connect(self.validate_data_s2)
        self.btnBrowseOutDir.clicked.connect(lambda: self.browse_dir(self.txtOutDir))
        self.txtOutDir.textChanged.connect(self.validate_data_s2)
        self.btnQuit.clicked.connect(self.quit)
        self.tabMain.currentChanged.connect(self.main_active_tab)
        self.tabDataMain.currentChanged.connect(self.data_active_tab)
        self.tabTrainingMain.currentChanged.connect(self.mod_active_tab)
        self.btnNext.clicked.connect(self.next_tab)
        self.btnBack.clicked.connect(self.back_tab)
        self.btnBrowse.clicked.connect(lambda: self.browse_file("Select raw data file", ["csv", "xlsx"], self.txtFileName, True))
        self.txtFileName.textChanged.connect(self.validate_data_s1)
        self.comboBoxTime.activated.connect(self.validate_data_s1)
        self.comboBoxLong.activated.connect(self.validate_data_s1)
        self.comboBoxLat.activated.connect(self.validate_data_s1)
        self.txtInputCRS.textChanged.connect(self.validate_data_s1)
        self.txtMeterCRS.textChanged.connect(self.validate_data_s1)
        self.btnBrowseShapeFile.clicked.connect(lambda: self.browse_file("Select shape file", ["csv", "shp"], self.lineShapeFilePath, False))
        self.comboBoxMapping.activated.connect(self.validate_data_s4)
        self.lineShapeFilePath.textChanged.connect(self.validate_data_s4)
        self.lineGridSizeVal.textChanged.connect(self.validate_data_s4)
        self.lineVoronoiCellSmallVal.textChanged.connect(self.validate_data_s4)
        self.lineVoronoiCellLargeVal.textChanged.connect(self.validate_data_s4)
        self.comboBoxPlotType.activated.connect(self.update_plot_config)
        self.btnDataPlot.clicked.connect(self.start_plotting)
        
        # initial value -- TRAINING
        self.float_params_line_edits = {
            'learning_rate': self.lineLr,
            'weight_decay': self.lineDecay,
            'lr_decay_factor': self.lineDecayFactor,
            'test_ratio': self.lineTestRat,
            'val_ratio': self.lineValRat,
            'momentum': self.lineMomentum,
        }
        self.int_params_line_edits = {
            'batch_size': self.lineBatch,
            'num_epochs': self.lineNEpoch,
        }
        self.numeric_line_model_config = {}
        self.comboBox_model_config = {}
        self.printer = None
        self.log_file_watcher = None
        # func connect -- MODEL
        for le in self.float_params_line_edits.values(): # params tab
            le.textChanged.connect(self.validate_model_params)
        for le in self.int_params_line_edits.values():
            le.textChanged.connect(self.validate_model_params)
        self.comboBoxModel.activated.connect(self.update_model_config)
        self.comboBoxOptim.activated.connect(self.validate_model_params)
        self.comboBoxScheduler.activated.connect(self.validate_model_params)
        self.comboBoxEarlyStop.activated.connect(self.validate_model_params)
        self.btnBrowseGraphData.clicked.connect(lambda: self.browse_file("Select graph data file", ["pt"], self.lineGraphData, False))
        self.lineGraphData.textChanged.connect(self.validate_model_params)
        self.btnBrowseLog.clicked.connect(lambda: self.browse_dir(self.txtLogDir)) # log tab
        self.radioBtnLocal.clicked.connect(self.validate_model_log)
        self.radioBtnWandb.clicked.connect(self.validate_model_log)
        self.radioBtnBoth.clicked.connect(self.validate_model_log)
        self.txtLogDir.textChanged.connect(self.validate_model_log)
        self.lineWandbToken.textChanged.connect(self.validate_model_log)
        self.lineWandbID.textChanged.connect(self.validate_model_log)
    
    # override the closeEvent function
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Confirm Exit", "Are you sure to quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
            
    def quit(self):
        response = QMessageBox.question(
            self,
            "Confirm Exit", "Are you sure to quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if response == QMessageBox.StandardButton.Yes:
            sys.exit()
        else:
            return
    
    def update_btn(self, index):
        if index == 0:
            self.data_active_tab()
        elif index == 1:
            self.mod_active_tab()

    # main tab (data or training)
    def main_active_tab(self):
        self.update_btn(self.tabMain.currentIndex())
                
    # under training tab
    def mod_active_tab(self):
        self.model_tab_index = self.tabTrainingMain.currentIndex()
        self.btnNext.setText("Train" if self.model_tab_index == 1 else "Next")
        if self.model_tab_index == 0:
            self.setup_mod_params()
            self.btnBack.hide()
        elif self.model_tab_index == 1:
            self.btnBack.show()
            self.validate_model_log()
        
    # under data tab
    def data_active_tab(self):
        self.data_tab_index = self.tabDataMain.currentIndex()
        self.btnNext.setText(
            "Map" if self.data_tab_index == 3
            else "Generate" if self.data_tab_index == 4
            else "To Train" if self.data_tab_index == 5 
            else "Next"
        )
        if self.data_tab_index == 0:
            self.btnBack.hide()
            self.validate_data_s1()
        else:
            self.btnBack.show()
        if self.data_tab_index == 1:
            self.gen_ui_data_s2()
            self.validate_data_s2()
        elif self.data_tab_index == 2:
            self.gen_ui_data_s3()
            self.btnNext.setEnabled(True)
        elif self.data_tab_index == 3:
            self.gen_ui_data_s4()
            self.validate_data_s4()
        elif self.data_tab_index == 4:
            self.gen_ui_data_s5()
            self.btnNext.setEnabled(True)
        elif self.data_tab_index == 5:
            self.gen_ui_data_s6()
            self.btnNext.setEnabled(True)
    
    def next_tab(self):
        # check current tab index (DATA or TRAINING)
        self.main_tab_idx = self.tabMain.currentIndex()
        # if DATA
        if self.main_tab_idx == 0:
            if self.data_tab_index == 5:
                self.setup_mod_params()
                self.tabMain.setCurrentIndex(self.main_tab_idx + 1) # 1
                self.main_tab_idx = self.tabMain.currentIndex()
                self.tabMain.setTabEnabled(self.main_tab_idx, True)
            else:
                if self.data_tab_index == 1:
                    self.start_preprocessing()
                    return
                if self.data_tab_index == 3:
                    self.start_mapping_task()
                    return
                if self.data_tab_index == 4:
                    self.start_data_gen()
                    return
                self.tabDataMain.setCurrentIndex(self.data_tab_index + 1)
                self.data_tab_index = self.tabDataMain.currentIndex()
                self.tabDataMain.setTabEnabled(self.data_tab_index, True)
        # if TRAINING
        elif self.main_tab_idx == 1:
            if self.model_tab_index == 0:
                self.start_create_model()
                return
            if self.model_tab_index == 1:
                self.start_training()
                return
            self.tabTrainingMain.setCurrentIndex(self.model_tab_index + 1)
            self.model_tab_index = self.tabTrainingMain.currentIndex()
            self.tabTrainingMain.setTabEnabled(self.model_tab_index, True)
            
    def back_tab(self):
        # check current tab index (DATA or TRAINING)
        self.main_tab_idx = self.tabMain.currentIndex()
        if self.main_tab_idx == 0: # DATA tab
            self.btnNext.setEnabled(True)
            self.tabDataMain.setCurrentIndex(self.data_tab_index - 1)
            self.data_tab_index = self.tabDataMain.currentIndex()
            if self.data_tab_index == 0:
                self.btnBack.hide()
        elif self.main_tab_idx == 1: # TRAINING tab
            self.btnNext.setEnabled(True)
            self.tabTrainingMain.setCurrentIndex(self.model_tab_index - 1)
            self.model_tab_index = self.tabTrainingMain.currentIndex()
            if self.model_tab_index == 0:
                self.btnBack.hide()
    
    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w:
                layout.removeWidget(w)
                w.deleteLater()     

    def init_ui(self):
        self.btnBack.hide()
        self.btnNext.setEnabled(False)
        self.tableInputView.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.labelGeoGuide.setText(
            "N.B. For accurate mapping result, refer to "
            '<a href="https://epsg.io/">epsg.io</a>'
            " to get the correct geodetic system code."
        )
        self.btn_style(self.btnBrowse, resource_path("images/open-file-khaki.svg"), "Browse")
        self.btn_style(self.btnBrowseOutDir, resource_path("images/open-file-khaki.svg"), "Browse")
        self.btn_style(self.btnBrowseLog, resource_path("images/open-file-purple.svg"), "Browse")
        self.btn_style(self.btnBrowseGraphData, resource_path("images/open-file-purple.svg"), "Browse")
        self.btn_style(self.btnBrowseShapeFile, resource_path("images/open-file-turquoise.svg"), "Browse")
        self.hide_components([self.btnBrowseShapeFile, self.lineShapeFilePath, self.labelParams2, 
                              self.lineVoronoiCellSmallVal, self.lineVoronoiCellLargeVal, self.labelLrPatience, self.lineLrPatience])
        for i in range(1, self.tabDataMain.count()):
            self.tabDataMain.setTabEnabled(i, False)
        for i in range(1, self.tabTrainingMain.count()):
            self.tabTrainingMain.setTabEnabled(i, False)
    
    # ********** START GENREIC FUNCS FOR REUSE  *********
    # *****************************************************
    def btn_style(self, btn, icon, tooltip, size=25, set_style=True):
        btn.setIcon(QIcon(icon))
        btn.setIconSize(QSize(size, size))
        btn.setToolTip(tooltip)
        if set_style:
            btn.setStyleSheet("""QPushButton {border: none;}""")

    def set_enabled_components(self, comp_list, type=True):
        for com in comp_list:
            com.setEnabled(type)

    def hide_components(self, comp_list):
        for com in comp_list:
            com.hide()

    def show_components(self, comp_list):
        for com in comp_list:
            com.show()

    def check_number_constraints(self, lines_dict, converter):
        is_ok = True
        vals = {}
        for name, le in lines_dict.items():
            text = le.text().strip()
            try:
                vals[name] = converter(text)
                le.setStyleSheet("")  
            except (ValueError, TypeError):
                is_ok = False
                le.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
        return is_ok, vals
    
    def create_gif(self):
        loading_spinner  = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        loading_spinner.setScaledContents(True)
        movie = QMovie(resource_path("images/loading_1.gif"))
        loading_spinner.setMovie(movie)
        return loading_spinner, movie
    
    def update_cfg(self, cfg, params_filtered_out, cb_filter_list, validate_func, cb_dict, numeric_dict, layout, inp_w):
        for index, (k, v) in enumerate(cfg.items()):
            row = index // 2
            pair = index % 2 # col
            col_label = pair * 2
            col_user_input = pair * 2 + 1

            label = QLabel(str(k))
            label.setStyleSheet("""font-size: 12pt; font-weight: normal""")
            label.setToolTip(v[-1])
            if k not in params_filtered_out:
                if k in cb_filter_list:
                    user_inp = QComboBox()
                    user_inp.setStyleSheet("""font-size: 12pt; font-weight: normal""")
                    cb_dict[k] = user_inp
                    user_inp.activated.connect(validate_func)
                    if k == "View":
                        user_inp.addItem('2d')
                        user_inp.addItem('3d')
                    elif k == "Selection method":
                        user_inp.addItem('random')
                        user_inp.addItem('highest activity')
                    else: # == temporal pooling
                        user_inp.addItem('last')
                        user_inp.addItem('mean')
                        user_inp.addItem('max')
                else: 
                    user_inp = QLineEdit()
                    numeric_dict[k] = user_inp
                    user_inp.textChanged.connect(validate_func)
                    user_inp.setStyleSheet("""font-size: 12pt; font-weight: normal""")
                user_inp.setFixedWidth(inp_w)
                layout.addWidget(label,  row, col_label)
                layout.addWidget(user_inp, row, col_user_input)
    
    def update_nav_buttons(self, viewer, btnPrev, btnNext):
        fl = viewer.file_list
        idx = viewer.current_index
        btnPrev.setEnabled(bool(fl) and idx > 0)
        btnNext.setEnabled(bool(fl) and idx < len(fl) - 1)

    def on_prev(self, viewer, btnPrev, btnNext):
        viewer.prev_file()
        self.update_nav_buttons(viewer, btnPrev, btnNext)

    def on_next(self, viewer, btnPrev, btnNext):
        viewer.next_file()
        self.update_nav_buttons(viewer, btnPrev, btnNext)

    def browse_dir(self, line_edit):
        fname = QFileDialog.getExistingDirectory(self, "Select Folder")
        if fname:
            line_edit.setText(fname)
    
    def browse_file(self, caption, filter_list, line_edit, preview_raw=False):
        fname = QFileDialog.getOpenFileName(
            parent=self,
            directory=os.getenv("HOME"),
            caption=caption,
        )
        file_extension = fname[0].split(".")[-1]
        if fname[0]:
            if file_extension not in filter_list:
                warning_message = "Please select file in .{} format!".format(" or .".join(filter_list) )
                QMessageBox.warning(
                    self, "Invalid File", warning_message
                )
                return
            line_edit.setText(fname[0])
            if preview_raw: # for loading preview raw data (in first step)
                CONFIG['data_path'] = fname[0]
                if CONFIG['data_path'].lower().endswith(".csv"):
                    self.loaded_data = pd.read_csv(CONFIG['data_path'], nrows=1000)
                else: # xlxs
                    self.loaded_data = pd.read_excel(CONFIG['data_path'], nrows=1000)
                if self.loaded_data is not None:
                    self.comboBoxTime.clear()
                    self.comboBoxLong.clear()
                    self.comboBoxLat.clear()
                    self.column_names = [str(x) for x in self.loaded_data.columns]
                    self.comboBoxTime.addItems(self.column_names)
                    self.comboBoxLong.addItems(self.column_names)
                    self.comboBoxLat.addItems(self.column_names)
                    self.preview()

    # *************************************************
    # ********** END GENREIC FUNCS FOR REUSE  *********

    # ********** START DATA TAB UI AND VALIDATE  *********
    # *****************************************************
    def gen_ui_data_s2(self):
        if getattr(self, "_s2_ui_built", False):
            return
        self._s2_ui_built = True
        self.hide_components([self.dateEditStart, self.dateEditEnd, self.checkOSMPoi, self.checkOSMRoad, self.checkOSMJunction])
        # Loading gif
        self.spinnerPreprocess, self.moviePreprocess = self.create_gif()
        self.spinnerPreprocess.hide()
        self.vLayoutSpinnerPreprocess.addWidget(self.spinnerPreprocess)

    def gen_ui_data_s3(self):       
        if getattr(self, "_s3_ui_built", False):
            return
        self._s3_ui_built = True

        # data stats display 
        lab_data_shape = QLabel(f"Processed dataset shape: {self.geo_df.shape}", self)
        lab_data_shape.setStyleSheet("""font-size: 12pt; font-weight: normal""")
        self.vLayoutDataStats.addWidget(lab_data_shape, 0)
        lab_time_range = QLabel(f"Time range: {self.geo_df[CONFIG['time_column']].min()} to {self.geo_df[CONFIG['time_column']].max()}", self)
        lab_time_range.setStyleSheet("""font-size: 12pt; font-weight: normal;""")    
        self.vLayoutDataStats.addWidget(lab_time_range, 1)
                    
        # control buttons for pdf image
        self.btnPrevStats = QPushButton()
        self.btn_style(self.btnPrevStats, resource_path("images/prev.svg"), "Previous", 25, False)
        self.btnNextStats = QPushButton()
        self.btn_style(self.btnNextStats, resource_path("images/next.svg"), "Next", 25, False)
        self.btnZoomIn = QPushButton()
        self.btn_style(self.btnZoomIn, resource_path("images/zoom-in.svg"), "Zoom In", 30, False)
        self.btnZoomOut = QPushButton()
        self.btn_style(self.btnZoomOut, resource_path("images/zoom-out.svg"), "Zoom Out", 30, False)
        self.btnSave = QPushButton()
        self.btn_style(self.btnSave, resource_path("images/save.svg"), "Save As", 30, False)
        self.horizonLayoutCtrl.addWidget(self.btnPrevStats)
        self.horizonLayoutCtrl.addWidget(self.btnNextStats)
        self.horizonLayoutCtrl.addWidget(self.btnZoomIn)
        self.horizonLayoutCtrl.addWidget(self.btnZoomOut)
        self.horizonLayoutCtrl.addWidget(self.btnSave)
        
        # pdf viewer area
        self.viewer = PdfViewerWidget()
        self.vertlLayoutDataStats.addWidget(self.viewer, stretch=0)
        
        # Connect controls
        self.btnPrevStats.clicked.connect(lambda: self.on_prev(self.viewer, self.btnPrevStats, self.btnNextStats))
        self.btnNextStats.clicked.connect(lambda: self.on_next(self.viewer, self.btnPrevStats, self.btnNextStats))
        self.btnZoomIn.clicked.connect(self.viewer.zoom_in)
        self.btnZoomOut.clicked.connect(self.viewer.zoom_out)
        self.btnSave.clicked.connect(self.viewer.save_as)
        self.viewer._load_folder(f'{CONFIG["output_dir"]}/preprocess')

    def gen_ui_data_s4(self):
        if getattr(self, "_s4_ui_built", False):
            return
        self._s4_ui_built = True
        self.lineVoronoiCellSmallVal.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.lineVoronoiCellLargeVal.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.lineGridSizeVal.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.spinner, self.movie = self.create_gif()
        self.spinner.hide()
        self.vLayoutSpinner.addWidget(self.spinner)

    def gen_ui_data_s5(self):
        if getattr(self, "_s5_ui_built", False):
            return
        self._s5_ui_built = True
        
        lab_num_regions = QLabel(f"Number of regions: {len(self.map_geo_df)}", self)
        lab_num_regions.setStyleSheet("font-size: 12pt; font-weight: normal")
        self.vLayoutMapInfo.addWidget(lab_num_regions, 0)
        lab_num_p2x_valid = QLabel(
            f"Points with valid mapping: {(self.point_to_x >= 0).sum()} of {len(self.point_to_x)}", self)
        lab_num_p2x_valid.setStyleSheet("font-size: 12pt; font-weight: normal")
        self.vLayoutMapInfo.addWidget(lab_num_p2x_valid, 1)

        # control buttons for pdf image
        self.btnPrevMap = QPushButton()
        self.btn_style(self.btnPrevMap, resource_path("images/prev.svg"), "Previous", 25, False)
        self.btnNextMap = QPushButton()
        self.btn_style(self.btnNextMap, resource_path("images/next.svg"), "Next", 25, False)
        self.btnZoomInMap = QPushButton()
        self.btn_style(self.btnZoomInMap, resource_path("images/zoom-in.svg"), "Zoom In", 30, False)
        self.btnZoomOutMap = QPushButton()
        self.btn_style(self.btnZoomOutMap, resource_path("images/zoom-out.svg"), "Zoom Out", 30, False)
        self.btnSaveVisual = QPushButton()
        self.btn_style(self.btnSaveVisual, resource_path("images/save.svg"), "Save As", 30, False)
        self.hLayoutCtrlMap.addWidget(self.btnPrevMap)
        self.hLayoutCtrlMap.addWidget(self.btnNextMap)
        self.hLayoutCtrlMap.addWidget(self.btnZoomInMap)
        self.hLayoutCtrlMap.addWidget(self.btnZoomOutMap)
        self.hLayoutCtrlMap.addWidget(self.btnSaveVisual)
        
        # pdf viewer area
        self.map_viewer = PdfViewerWidget()
        self.vLayoutMap.addWidget(self.map_viewer, stretch=0)
        
        # Connect controls
        self.btnPrevMap.clicked.connect(lambda: self.on_prev(self.map_viewer, self.btnPrevMap, self.btnNextMap))
        self.btnNextMap.clicked.connect(lambda: self.on_next(self.map_viewer, self.btnPrevMap, self.btnNextMap))
        self.btnZoomInMap .clicked.connect(self.map_viewer.zoom_in)
        self.btnZoomOutMap.clicked.connect(self.map_viewer.zoom_out)
        self.btnSaveVisual.clicked.connect(self.map_viewer.save_as)
        self.map_viewer._load_folder(f'{CONFIG["output_dir"]}/mapping')

        # loading gif
        self.spinnerMap, self.movieMap= self.create_gif()
        self.spinnerMap.hide()
        self.vLayoutSpinnerMap.addWidget(self.spinnerMap)
   
    def gen_ui_data_s6(self):
        if getattr(self, "_s6_ui_built", False):
            return
        self._s6_ui_built = True
        self.btnDataPlot.setEnabled(False)
        # config area
        self.gLayoutPlotConfig.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.gLayoutPlotConfig.setHorizontalSpacing(35)
        self.gLayoutPlotConfig.setVerticalSpacing(8)
        self.gLayoutPlotConfig.setColumnStretch(1, 1)
        self.gLayoutPlotConfig.setColumnStretch(3, 1)
        self.numeric_line_plot_config = {}
        self.comboBox_plot_config = {}
        self.update_cfg(CONFIG['plot_nodes'], [], ["View", 'Selection method'], self.validate_data_s6, 
                        self.comboBox_plot_config, self.numeric_line_plot_config, 
                        self.gLayoutPlotConfig, 150) # default plot nodes
        # control buttons for pdf image
        self.btnZoomInTGD = QPushButton()
        self.btn_style(self.btnZoomInTGD, resource_path("images/zoom-in.svg"), "Zoom In", 30, False)
        self.btnZoomOutTGD = QPushButton()
        self.btn_style(self.btnZoomOutTGD, resource_path("images/zoom-out.svg"), "Zoom Out", 30, False)
        self.btnSaveVisual = QPushButton()
        self.btn_style(self.btnSaveVisual, resource_path("images/save.svg"), "Save As", 30, False)
        self.hLayoutCtrlGraph.addWidget(self.btnZoomInTGD)
        self.hLayoutCtrlGraph.addWidget(self.btnZoomOutTGD)
        self.hLayoutCtrlGraph.addWidget(self.btnSaveVisual)
        # pdf viewer area
        self.tgd_viewer = PdfViewerWidget()
        self.vLayoutGraph.addWidget(self.tgd_viewer, stretch=0)
        # Connect controls
        self.btnZoomInTGD.clicked.connect(self.tgd_viewer.zoom_in)
        self.btnZoomOutTGD.clicked.connect(self.tgd_viewer.zoom_out)
        self.btnSaveVisual.clicked.connect(self.tgd_viewer.save_as)
        # loading gif
        self.spinnerTGD, self.movieTGD = self.create_gif()
        self.spinnerTGD.hide()
        self.vLayoutSpinnerTGD.addWidget(self.spinnerTGD)
        self.validate_data_s6()

    # CALL -- PREPROCESSING FUNCTION 
    def start_preprocessing(self):
        self.set_enabled_components([self.btnNext, self.btnBack, self.tabMain], False)
        self.spinnerPreprocess.show()
        self.moviePreprocess.start()
        self.prepocessor = Worker(process_task, CONFIG)
        self.prepocessor.finished.connect(self.on_preprocess_func_done)
        self.prepocessor.start()

    def on_preprocess_func_done(self, result):
        self.set_enabled_components([self.tabMain, self.btnBack, self.btnNext], True)
        self.moviePreprocess.stop()
        self.spinnerPreprocess.hide()
        self.geo_df = result["data"]
        self.tabDataMain.setCurrentIndex(2)
        self.data_tab_index = self.tabDataMain.currentIndex()
        self.tabDataMain.setTabEnabled(self.data_tab_index, True)

    # CALL -- MAPPING FUNCTION 
    def start_mapping_task(self):
        self.set_enabled_components([self.btnNext, self.btnBack, self.tabMain], False)
        self.spinner.show()
        self.movie.start()
        self.tabMain.setEnabled(False)
        self.map_worker = Worker(map_task, CONFIG, self.mapper, self.geo_df)
        self.map_worker.finished.connect(self.on_mapping_func_done)
        self.map_worker.start()

    def on_mapping_func_done(self, result):
        self.movie.stop()
        self.spinner.hide()
        self.set_enabled_components([self.tabMain, self.btnBack, self.btnNext], True)
        self.map_geo_df, self.point_to_x = result["data"]["res"]
        self.gdf_valid = result["data"]["geo_valid"]
        self.p2x_valid = result["data"]["p2x_valid"]
        self.tabDataMain.setCurrentIndex(4)
        self.data_tab_index = self.tabDataMain.currentIndex()
        self.tabDataMain.setTabEnabled(self.data_tab_index, True)

    # CALL -- GRAPH DATA GENERATE FUNC
    def start_data_gen(self):
        self.set_enabled_components([self.btnNext, self.btnBack, self.tabMain], False)
        self.spinnerMap.show()
        self.movieMap.start()
        self.tabMain.setEnabled(False)
        self.generator = Worker(generate_data_task, CONFIG, self.map_geo_df, self.gdf_valid, self.p2x_valid)
        self.generator.finished.connect(self.on_datagen_func_done)
        self.generator.start()

    def on_datagen_func_done(self, result):
        self.movieMap.stop()
        self.spinnerMap.hide()
        self.set_enabled_components([self.tabMain, self.btnBack, self.btnNext], True)
        self.graph_data = result["graph_data"]
        self.temporal_graph_dataset = result["temporal_graph_data"]
        if CONFIG["osm_types"] is not None:
            self.osm_checked_list = ", ".join(CONFIG["osm_types"])
            self.osm_extracted_features = result["osm_features"]
            QMessageBox.information(
                self, "Information", "Temporal graph data generated successfully.\nData saved to the selected output directory.\n"
                f"Number of nodes: {result['num_nodes']}\n"
                f"Number of edges: {result['num_edges']}\n"
                f"Number of extracted OpenStreetMap (UKG) features: {result['num_extracted_osm_features']} from {self.osm_checked_list}\n"
                f"Number of node's features: {self.temporal_graph_dataset.features[0].shape[-1]}\n"
                f"Dataset shape {(len(self.temporal_graph_dataset.features), *self.temporal_graph_dataset.features[0].shape)}. Format: [total time steps, num_nodes, History window, in_channels]\n"
                "\n\nN.B. You can skip next step and go to Training tab if you do not want to visualize the graph data."
            )
        else:
            QMessageBox.information(
                self, "Information", "Temporal graph data generated successfully.\nData saved to the selected output directory.\n"
                f"Number of nodes: {result['num_nodes']}\n"
                f"Number of edges: {result['num_edges']}\n"
                f"Number of node's features: {self.temporal_graph_dataset.features[0].shape[-1]}\n"
                f"Dataset shape {(len(self.temporal_graph_dataset.features), *self.temporal_graph_dataset.features[0].shape)}. Format: [total time steps, num_nodes, History window, in_channels]\n"
                "\n\nN.B. You can skip next step and go to Training tab if you do not want to visualize the graph data."
            )
        self.tabDataMain.setCurrentIndex(5)
        self.data_tab_index = self.tabDataMain.currentIndex()
        self.tabDataMain.setTabEnabled(self.data_tab_index, True)

    # CALL -- DATA PLOT FUNC
    def start_plotting(self):
        self.spinnerTGD.show()
        self.movieTGD.start()
        self.set_enabled_components([self.btnDataPlot, self.btnBack, self.btnNext, self.tabMain], False)
        self.plot_worker = Worker(plot_task, CONFIG, 
                                  self.temporal_graph_dataset, self.graph_data, 
                                  self.osm_extracted_features, self.map_geo_df)
        self.plot_worker.finished.connect(self.on_plotting_func_done)
        self.plot_worker.start()

    def on_plotting_func_done(self):
        self.movieTGD.stop()
        self.spinnerTGD.hide()
        self.set_enabled_components([self.btnDataPlot, self.btnBack, self.btnNext, self.tabMain], True)
        if CONFIG["plot_type"] == 'node':
            self.tgd_viewer._load_file(f'{CONFIG["output_dir"]}/graph/time_series_{CONFIG["plot_nodes"]["View"][0]}.pdf')
        elif CONFIG["plot_type"] == 'heatmap':
            self.tgd_viewer._load_file(f'{CONFIG["output_dir"]}/graph/temporal_heatmap.pdf')
        else: # spatial:
            self.tgd_viewer._load_file(f'{CONFIG["output_dir"]}/graph/spatial_network.pdf')

    def validate_data_s1(self):
        is_valid_icrs = False
        # check epsg -- input
        if re.match(crs_pattern, self.txtInputCRS.text()):
            self.txtInputCRS.setStyleSheet("")
            CONFIG["input_crs"] = self.txtInputCRS.text().upper()
            is_valid_icrs = True
        else:
            self.txtInputCRS.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
        is_valid_mcrs = False
        # check epsg -- meter
        if re.match(crs_pattern, self.txtMeterCRS.text()):
            self.txtMeterCRS.setStyleSheet("")
            CONFIG["meter_crs"] = self.txtMeterCRS.text().upper()
            is_valid_mcrs = True
        else:
            self.txtMeterCRS.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
        if self.txtFileName.text() != "":
            CONFIG["time_column"] = self.comboBoxTime.currentText()
            CONFIG["long_column"] = self.comboBoxLong.currentText()
            CONFIG["lat_column"] = self.comboBoxLat.currentText()
        self.btnNext.setEnabled(is_valid_icrs and is_valid_mcrs and CONFIG['data_path'] != "")

    def validate_data_s2(self):
        # check appplication type
        if self.comboBoxOutType.currentText().__contains__("Regression"):
            CONFIG["app_type"] = "regression"
        else:
            CONFIG["app_type"] = "classification"

        # check data filters
        if self.comboBoxFilterDS.currentText() == "Yes":
            self.dateEditStart.show()
            self.filter_start_date = self.dateEditStart.date()
        else:
            self.dateEditStart.hide()
            self.filter_start_date = None
        if self.comboBoxFilterDE.currentText() == "Yes":
            self.dateEditEnd.show()
            self.filter_end_date = self.dateEditEnd.date()
        else:
            self.dateEditEnd.hide()
            self.filter_end_date = None
        
        if self.filter_start_date and self.filter_end_date:
            self.dateEditEnd.setMinimumDate(self.filter_start_date.addDays(1))
            self.dateEditStart.setMaximumDate(self.filter_end_date.addDays(-1))        

        if self.filter_start_date:
            CONFIG["date_filter_start"] = self.dateEditStart.date().toString("dd-MM-yyyy") + " 23:59:59"
        else:
            CONFIG["date_filter_start"] = None

        if self.filter_end_date:	
            CONFIG["date_filter_end"] = self.dateEditEnd.date().toString("dd-MM-yyyy") + " 23:59:59"
        else:
            CONFIG["date_filter_end"] = None

        # check integers line edits
        is_ok_ints, _ = self.check_number_constraints(self.data_int_line_edits, int)

        # check testing mode
        if self.comboBoxTestMode.currentText() == "True":
            CONFIG["test_mode"] = True
            for _, le in self.bounds_line_edits.items():
                le.setEnabled(True)
        else:
            CONFIG["test_mode"] = False
            CONFIG["bounds"] = None
            for _, le in self.bounds_line_edits.items():
                le.setEnabled(False)
                le.setStyleSheet("")

        # check bounds line edits
        is_ok_bounds = True
        if CONFIG["test_mode"]:
            is_ok_bounds, bound_vals = self.check_number_constraints(self.bounds_line_edits, float)
            if is_ok_bounds:
                if not (bound_vals['maxLon'] > bound_vals['minLon'] and bound_vals['maxLat'] > bound_vals['minLat']):
                    is_ok_bounds = False
                    if bound_vals.get('maxLon', 0) <= bound_vals.get('minLon', 0):
                        self.lineMaxLong .setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                        self.lineMinLong .setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                    if bound_vals.get('maxLat', 0) <= bound_vals.get('minLat', 0):
                        self.lineMaxLat  .setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                        self.lineMinLat  .setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                if self.lineMaxLong.text() !="" and self.lineMinLong.text() != "" and \
                    self.lineMaxLat.text() != "" and self.lineMinLat.text() != "" and \
                    bound_vals['maxLon'] > bound_vals['minLon'] and bound_vals['maxLat'] > bound_vals['minLat']:
                    CONFIG["bounds"] = {"min_lat": bound_vals['minLat'],
                                        "max_lat": bound_vals['maxLat'],
                                        "min_lon": bound_vals['minLon'],
                                        "max_lon": bound_vals['maxLon'],
                                        }
        
        # check OSM (knowledge graph)
        is_ok_OSM = True
        if self.comboBoxUKG.currentText() == "True":
            self.checkOSMPoi.show()
            self.checkOSMRoad.show()
            self.checkOSMJunction.show()
            CONFIG["osm_types"] = [
                w.text()
                for i in range(self.hLayoutOsm.count())
                for w in (self.hLayoutOsm.itemAt(i).widget(),)
                if isinstance(w, QCheckBox) and w.isChecked()
            ]
            if len(CONFIG["osm_types"]) == 0:
                is_ok_OSM = False
        else:
            self.checkOSMPoi.hide()
            self.checkOSMRoad.hide()
            self.checkOSMJunction.hide()
            CONFIG["osm_types"] = None

        # check outdir 
        CONFIG["output_dir"] = self.txtOutDir.text() if self.txtOutDir.text() != "" else None
        
        self.btnNext.setEnabled(is_ok_ints and is_ok_bounds and is_ok_OSM and CONFIG["output_dir"] is not None)
        
    def validate_data_s4(self):
        CONFIG["mapping"] = self.comboBoxMapping.currentText()
        self.update_mapping_config(CONFIG["mapping"])
        is_valid = True
        line_dict = {}
        if CONFIG["mapping"] == 'grid':
            line_dict = {
                'gridSize': self.lineGridSizeVal,
            }
            is_valid, grid_dict = self.check_number_constraints(line_dict, int)
            if is_valid:
                CONFIG['cell_size'] = grid_dict['gridSize']
                if CONFIG['cell_size'] <= 0:
                    is_valid = False
                    self.lineGridSizeVal.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
            self.mapper = stm_graph.GridMapping(cell_size=CONFIG['cell_size'], target_crs=CONFIG['meter_crs'])
        if CONFIG["mapping"] == 'administrative':
            if self.lineShapeFilePath.text():
                CONFIG["adm_shape_file"] = self.lineShapeFilePath.text()
                self.lineShapeFilePath.setStyleSheet("")
            else:
                is_valid = False
                self.lineShapeFilePath.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
            self.mapper = stm_graph.AdministrativeMapping(
                admin_type="administrative",
                districts_file=CONFIG['adm_shape_file'],
                input_crs=CONFIG['input_crs'],
                meter_crs=CONFIG['meter_crs']
            )
        if CONFIG["mapping"] == 'voronoi-based':
            line_dict = {
                'voronoiSmallSize': self.lineVoronoiCellSmallVal,
                'voronoiLargeSize': self.lineVoronoiCellLargeVal,
            }
            is_valid, voronoi_dict = self.check_number_constraints(line_dict, int)
            if is_valid:
                self.voronoiSmallSize = voronoi_dict['voronoiSmallSize']
                self.voronoiLargeSize = voronoi_dict['voronoiLargeSize']
                if self.voronoiSmallSize <= 0:
                    is_valid = False
                    self.lineVoronoiCellSmallVal.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                if self.voronoiLargeSize <= 0:
                    is_valid = False
                    self.lineVoronoiCellLargeVal.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                if self.voronoiLargeSize <= self.voronoiSmallSize:
                    is_valid = False
                    self.lineVoronoiCellLargeVal.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                    self.lineVoronoiCellSmallVal.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
            self.mapper = stm_graph.VoronoiDegreeMapping(
                place_name=None, testing_mode=False, buffer_distance=0.05,
                large_cell_size=CONFIG['vor_big_cell_size'], 
                small_cell_size=CONFIG['vor_small_cell_size']
            )
        self.btnNext.setEnabled(is_valid)
    
    def validate_data_s6(self):
        is_ok = True
        if len(self.numeric_line_plot_config): 
            is_ok, vals = self.check_number_constraints(self.numeric_line_plot_config, int)
        if is_ok:
            if CONFIG["plot_type"] == "node":
                for k in CONFIG["plot_nodes"].keys():
                    if k in vals.keys():
                        CONFIG["plot_nodes"][k][0] = vals[k]
                if self.comboBox_plot_config["Selection method"].currentText() == "random":
                    CONFIG["plot_nodes"]["Selection method"][0] = 'random'
                else:
                    CONFIG["plot_nodes"]["Selection method"][0] = 'highest_activity'
                CONFIG["plot_nodes"]["View"][0] = self.comboBox_plot_config["View"].currentText()
            elif CONFIG["plot_type"] == "heatmap":
                for k in CONFIG["plot_heatmap"].keys():
                    if k in vals.keys():
                        CONFIG["plot_heatmap"][k][0] = vals[k]
                if self.comboBox_plot_config["Selection method"].currentText() == "random":
                    CONFIG["plot_heatmap"]["Selection method"][0] = 'random'
                else:
                    CONFIG["plot_heatmap"]["Selection method"][0] = 'highest_activity'
            else: # spatial
                for k in CONFIG["plot_spatial"].keys():
                    if k in vals.keys():
                        CONFIG["plot_spatial"][k][0] = vals[k]
            
        self.btnDataPlot.setEnabled(is_ok)

    def update_plot_config(self):
        self.clear_layout(self.gLayoutPlotConfig)
        chosen_plot_type = self.comboBoxPlotType.currentText()
        if chosen_plot_type.__contains__("nodes"):
            CONFIG["plot_type"] = 'node'
        elif chosen_plot_type.__contains__("heatmap"):
            CONFIG["plot_type"] = 'heatmap'
        else:
            CONFIG["plot_type"] = 'spatial'
        conf_load = {}
        if CONFIG["plot_type"] == 'node':
            conf_load = CONFIG['plot_nodes']
        elif CONFIG["plot_type"] == 'heatmap':
            conf_load = CONFIG['plot_heatmap']
        else: 
            conf_load = CONFIG['plot_spatial']
        self.numeric_line_plot_config = {}
        self.comboBox_plot_config = {}
        self.update_cfg(conf_load, [], 
                        ["View", 'Selection method'], self.validate_data_s6, 
                        self.comboBox_plot_config, self.numeric_line_plot_config, 
                        self.gLayoutPlotConfig, 150)
  
    def update_mapping_config(self, mapping):
        grid_comps = [self.lineGridSizeVal]
        adm_comps = [self.btnBrowseShapeFile, self.lineShapeFilePath]
        voronoi_comps = [self.lineVoronoiCellSmallVal, self.lineVoronoiCellLargeVal, self.labelParams2]
        if mapping == 'grid':
            self.labelParams1.setText("Cell Size (m)")
            self.hide_components(adm_comps + voronoi_comps)
            self.show_components(grid_comps)
        elif mapping == 'administrative':
            self.labelParams1.setText("Shape file")
            self.hide_components(grid_comps + voronoi_comps)
            self.show_components(adm_comps)
        elif mapping == 'voronoi-based':
            self.labelParams1.setText("Small Cell Size (m)")  
            self.hide_components(grid_comps + adm_comps)
            self.show_components(voronoi_comps)

    def preview(self):
        if self.loaded_data is not None:
            num_rows_limited = 15  # limit to 15 rows
            num_cols = len(self.column_names)
            self.tableInputView.setColumnCount(num_cols)
            self.tableInputView.setRowCount(num_rows_limited)
            self.tableInputView.setHorizontalHeaderLabels(self.column_names)
            for i in range(num_rows_limited):
                for j in range(num_cols):
                    self.tableInputView.setItem(
                        i, j, QTableWidgetItem(str(self.loaded_data.iloc[i, j]))
                    )
            self.tableInputView.resizeColumnsToContents()    
    # *****************************************************
    # *********** END DATA TAB UI AND FUNCTIONS  **********
    
    # ********** START MODEL/TRAINING TAB UI AND FUNCTIONS  *********
    # ***************************************************************
    def setup_mod_params(self):
        if getattr(self, "_model_params_ui_built", False):
            return
        self._model_params_ui_built = True
        # model params area
        self.gLayoutModelParams.setHorizontalSpacing(45)
        self.gLayoutModelParams.setVerticalSpacing(12)
        # columns 0+2 labels; 1+3 edits (stretching)
        self.gLayoutModelParams.setColumnStretch(1, 1)
        self.gLayoutModelParams.setColumnStretch(3, 1)
        self.numeric_line_model_config= {}
        self.comboBox_model_config = {}
        self.update_cfg(CONFIG["training"]["gcn"], # default GCN model
                        ["in_channels", "out_channels", "num_nodes", "k", "K", "history_window", "kernel_size"], 
                        ["temporal_pooling"], self.validate_model_params, 
                        self.comboBox_model_config, self.numeric_line_model_config, 
                        self.gLayoutModelParams, 150)
        self.validate_model_params()
        
    def update_model_config(self):
        self.clear_layout(self.gLayoutModelParams)
        selected_model = self.comboBoxModel.currentText().lower()
        self.numeric_line_model_config= {}
        self.comboBox_model_config = {}
        CONFIG["training"]["model"] = selected_model
        self.update_cfg(CONFIG["training"][selected_model],
                        ["in_channels", "out_channels", "num_nodes", "k", "K", "history_window", "kernel_size"], 
                        ["temporal_pooling"], self.validate_model_params, 
                        self.comboBox_model_config, self.numeric_line_model_config, 
                        self.gLayoutModelParams, 150)
           
    def validate_model_params(self):
        # optim
        CONFIG["training"]["optimizer_name"] = self.comboBoxOptim.currentText().lower()
        if CONFIG["training"]["optimizer_name"] == 'sgd':
            self.labelMomentum.show()
            self.lineMomentum.show()
            self.float_params_line_edits["momentum"] = self.lineMomentum
        else:
            self.labelMomentum.hide()
            self.lineMomentum.hide()
            self.float_params_line_edits.pop('momentum', None)
        # lr scheduler type
        CONFIG["training"]["scheduler_type"] = self.comboBoxScheduler.currentText().lower()
        if CONFIG["training"]["scheduler_type"] == 'step':
            self.hide_components([self.labelLrPatience, self.lineLrPatience])
            self.show_components([self.labelStepDecay, self.lineStepDecay])
            self.int_params_line_edits["lr_step_decay"] = self.lineStepDecay
            self.int_params_line_edits.pop("lr_patience", None)
        elif CONFIG["training"]["scheduler_type"] == 'plateau':
            self.hide_components([self.labelStepDecay, self.lineStepDecay])
            self.show_components([self.labelLrPatience, self.lineLrPatience])
            self.int_params_line_edits["lr_patience"] = self.lineLrPatience
            self.int_params_line_edits.pop("lr_step_decay", None)
        else: # lr scheduler = None
            self.hide_components([self.labelLrPatience, self.lineLrPatience, self.labelStepDecay, self.lineStepDecay])
            self.int_params_line_edits.pop("lr_step_decay", None)
            self.int_params_line_edits.pop("lr_patience", None)
        # earlystop
        CONFIG["training"]["early_stopping"] = self.comboBoxEarlyStop.currentText()
        if CONFIG["training"]["early_stopping"] == 'False':
            self.hide_components([self.labelEsPatience, self.lineEsPatience])
            self.int_params_line_edits.pop("lr_step_decay", None)
        else:
            self.show_components([self.labelEsPatience, self.lineEsPatience])
            self.int_params_line_edits["es_patience"] = self.lineEsPatience

        # check training params 
        is_ok_int_training, int_vals = self.check_number_constraints(self.int_params_line_edits, int)
        if is_ok_int_training:
            for k in int_vals:
                if k in CONFIG["training"]:
                    CONFIG["training"][k] = int_vals[k]   
        is_ok_float_training, float_vals = self.check_number_constraints(self.float_params_line_edits, float)    
        if is_ok_float_training:
            for k in float_vals:
                if k in ["test_ratio", "val_ratio"]:
                    if float_vals[k] <= 0 or float_vals[k] >= 1:
                        is_ok_float_training = False
                        self.float_params_line_edits[k].setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                    else:
                        self.float_params_line_edits[k].setStyleSheet("")
                        CONFIG["training"][k] = float_vals[k]
                if k in ["momentum", "learning_rate", "weight_decay"]:
                    if float_vals[k] < 0:
                        is_ok_float_training = False
                        self.float_params_line_edits[k].setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                    else:
                        self.float_params_line_edits[k].setStyleSheet("")
                        CONFIG["training"][k] = float_vals[k]
                if k == "lr_decay_factor":
                    if float_vals[k] >= 1:
                        self.float_params_line_edits[k].setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                        is_ok_float_training = False
                    else:
                        self.float_params_line_edits[k].setStyleSheet("")
                        CONFIG["training"][k] = float_vals[k]

        # check model params
        self.int_params_model = {}
        self.float_params_model = {}
        if (len(self.numeric_line_model_config)):
            for k in self.numeric_line_model_config:
                if k == "dropout":
                    self.float_params_model[k] = self.numeric_line_model_config[k]
                else:
                    self.int_params_model[k] = self.numeric_line_model_config[k]
        is_ok_float_model, float_vals = self.check_number_constraints(self.float_params_model, float)
        if is_ok_float_model:
            for k in float_vals:
                if k == "dropout":
                    if float_vals[k] < 0 or float_vals[k] > 1:
                        self.float_params_model[k].setStyleSheet("background: rgba(255, 0, 0, 0.3);")
                        is_ok_float_model = False
                    else:
                        self.float_params_model[k].setStyleSheet("")
                        CONFIG["training"][CONFIG["training"]["model"]][k][0] = float_vals[k]
        is_ok_int_model, int_vals = self.check_number_constraints(self.int_params_model, int)
        if is_ok_int_model:
            for k in int_vals:
                CONFIG["training"][CONFIG["training"]["model"]][k][0] = int_vals[k] 

        # add model params combobox
        for k in self.comboBox_model_config:
            if k in CONFIG["training"][CONFIG["training"]["model"]]:
                CONFIG["training"][CONFIG["training"]["model"]][k][0] = self.comboBox_model_config[k].currentText()

        # check graph data file 
        is_ok_data_file = False
        if self.lineGraphData.text():
            CONFIG["training"]["graph_data_path"] = self.lineGraphData.text()
            is_ok_data_file = True
            self.lineGraphData.setStyleSheet("")
        else:
            self.lineGraphData.setStyleSheet("background: rgba(255, 0, 0, 0.3);")
        self.btnNext.setEnabled(is_ok_int_training and is_ok_float_training and is_ok_int_model and is_ok_float_model and is_ok_data_file)

    def validate_model_log(self):
        self.log_type = 'wandb'
        if self.radioBtnLocal.isChecked(): # chose local log
            self.set_enabled_components([self.btnBrowseLog, self.txtLogDir, self.plainLogPrint], True)
            self.set_enabled_components([self.lineWandbToken, self.lineWandbID, self.lineWandbExp], False)
            self.log_type = "local"
        if self.radioBtnWandb.isChecked(): # choose wandb
            self.set_enabled_components([self.btnBrowseLog, self.txtLogDir, self.plainLogPrint], False)
            self.set_enabled_components([self.lineWandbToken, self.lineWandbID, self.lineWandbExp], True)
            self.log_type = "wandb"
        if self.radioBtnBoth.isChecked(): # choose both
            self.set_enabled_components([self.btnBrowseLog, self.txtLogDir, self.plainLogPrint,
                                         self.lineWandbToken, self.lineWandbID, self.lineWandbExp], True)
            self.log_type = "both"
        CONFIG["training"]["use_wandb"] = True if self.log_type in ["wandb", "both"] else False
        CONFIG["training"]["experiment_name"] = self.lineWandbExp.text() if self.log_type in ['wandb', 'both'] else "stm_graph_experiment"
        if self.log_type in ['wandb', 'both']:
            self.plainLogPrint.clear()
            CONFIG["training"]["wandb_api_key"] = self.lineWandbToken.text()
            CONFIG["training"]["wandb_project"] = self.lineWandbID.text()
            if self.log_type == "wandb":
                CONFIG["training"]["log_dir"] = "out" if CONFIG["output_dir"] is None else CONFIG["output_dir"]
                self.btnNext.setEnabled(bool(self.lineWandbToken.text().strip()) and bool(self.lineWandbID.text().strip()) and  bool(self.lineWandbExp.text().strip()))
            else:
                self.btnNext.setEnabled(bool(self.lineWandbToken.text().strip()) and bool(self.lineWandbID.text().strip()) and  bool(self.lineWandbExp.text().strip()) and bool(self.txtLogDir.text().strip()))
                CONFIG["training"]["log_dir"] = self.txtLogDir.text()
        else: # local 
            CONFIG["training"]["log_dir"] = self.txtLogDir.text() 
            self.btnNext.setEnabled(bool(CONFIG["training"]["log_dir"].strip()))
    
    # CALL -- CREATE MODEL FUNC
    def start_create_model(self):
        self.set_enabled_components([self.btnNext, self.tabMain], False)
        stat_feat_count = self.osm_extracted_features.shape[1] if self.osm_extracted_features is not None else 0
        self.loaded_temporal_dataset = torch.load(CONFIG["training"]["graph_data_path"]) #4d
        if CONFIG["training"]["model"] in ["gcn", "tgcn"]:
            self.loaded_temporal_dataset = stm_graph.convert_4d_to_3d_dataset(self.loaded_temporal_dataset, static_features_count=stat_feat_count) #3d
        CONFIG["training"][CONFIG["training"]["model"]]["in_channels"][0] = self.loaded_temporal_dataset.features[0].shape[-1]
        if "num_nodes" in CONFIG["training"][CONFIG["training"]["model"]]:
            CONFIG["training"][CONFIG["training"]["model"]]["num_nodes"][0] = self.loaded_temporal_dataset.features[0].shape[0]
        kernel_list = [x for x in ('k', 'K', 'kernel_size', 'history_window') if x in CONFIG["training"][CONFIG["training"]["model"]]]
        if len(kernel_list):
            for k in kernel_list:
                CONFIG["training"][CONFIG["training"]["model"]][k][0] = CONFIG["window_size"]
        self.model_factory = Worker(create_model_task, CONFIG)
        self.model_factory.finished.connect(self.on_create_model_func_done)
        self.model_factory.start()
        
    def on_create_model_func_done(self, result):
        self.set_enabled_components([self.tabMain, self.btnNext], True)
        self.model = result["model"]
        QMessageBox.information(
            self, "Information", "Model created successfully."
        )
        self.tabTrainingMain.setCurrentIndex(self.tabTrainingMain.currentIndex()+1)
        self.mod_tab_index = self.tabTrainingMain.currentIndex()
        self.tabTrainingMain.setTabEnabled(self.mod_tab_index, True)        
        
    # CALL -- TRAINING FUNC
    def start_training(self):
        self.set_enabled_components([self.tabMain, self.btnBack, self.btnNext], False)
        self.plainLogPrint.setEnabled(True)
        self.trainer = Worker(training_task, CONFIG, self.model, self.loaded_temporal_dataset)
        self.trainer.finished.connect(self.on_training_func_done)
        self.trainer.start()
        if self.log_type in ["local", "both"]:
            time.sleep(1)
            self.log_watcher = LFW(folder=CONFIG["training"]["log_dir"])
            self.log_watcher.logfile_found.connect(self.start_log_printer)
            self.log_watcher.start()
    
    def start_log_printer(self, logfile):
        self.printer = LP(logfile)
        self.printer.newLine.connect(self.log_append)
        self.printer.start()
        self.log_watcher.stop()

    def log_append(self, line):
        self.plainLogPrint.appendPlainText(line)

    def on_training_func_done(self):
        self.set_enabled_components([self.tabMain, self.btnBack, self.btnNext], True)
        QMessageBox.information(
            self, "Information", "Training process done and stopped."
        )
        if self.log_type in ["local", "both"] and self.printer and self.printer.isRunning():
            self.printer.stop()
    
    # ***************************************************************
    # ********** END MODEL/TRAINING TAB UI AND FUNCTIONS  **********

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())