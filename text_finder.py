from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import configparser
import os
import threading
import queue
import time
import logging
import locale
import re

import pandas as pd
import xlrd
import docx2txt
from odf import text, teletype
from odf.opendocument import load
import io
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO


from about_dialog import Ui_about_dialog
from help_dialog import Ui_help_dialog

# Version:
Version = 1.0

# Global Variables:
Stop_pressed = False
Queueing_done = False
Queue_handler_done = False

# Queue related:
Other_queue = queue.Queue()
Docx_queue = queue.Queue()
Xlsx_queue = queue.Queue()
Odt_queue = queue.Queue()
Pdf_queue = queue.Queue()
Output_queue = queue.Queue()

# Variables for status labels:
Files_queued = 0
Files_read = 0
Files_found = 0
Files_not_readable = 0
Status_Text = "Idle"

# Settings:

# settings for logging:
I_logger = logging.getLogger("Info")
E_logger = logging.getLogger("Error")
I_logger.setLevel(logging.INFO)
E_logger.setLevel(logging.ERROR)
Info_file_handler = logging.FileHandler("Info.log")
Error_file_handler = logging.FileHandler("Error.log")
Error_logging_format = logging.Formatter(
    "\n%(asctime)s:%(levelname)s:%(message)s")
Info_logging_format = logging.Formatter("%(asctime)s:%(message)s")
Info_file_handler.setFormatter(Info_logging_format)
Error_file_handler.setFormatter(Error_logging_format)
I_logger.addHandler(Info_file_handler)
E_logger.addHandler(Error_file_handler)

# The following file types are not searched, unless selected.
# docx, xlsx/xls, odt and pdf can be selected:
skipped_types = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff",
                 ".stl", ".blend", ".exe", ".zip", ".rar", ".ace", ".jar",
                 ".mp3", ".m3u", ".mp4", ".mpeg", ".vob", ".avi", ".flv",
                 ".wmv", ".m2ts", ".ts", ".wav", ".wma", ".dat", ".dll",
                 ".ppt", ".pps", ".pptx", ".doc", ".xls", ".xlsx", ".docx",
                 ".odt", ".pdf")
# Default settings:
Default_Search_String = ""
Default_Search_Path = "C:\\"
Search_other = True
Search_docx = True
Search_xlsx = True
Search_odt = True
Search_pdf = False
Logging_enabled = True
Regex_used = True

# read settings from file:
config = configparser.ConfigParser()
try:
    config.read("settings.ini")
except configparser.MissingSectionHeaderError:  # header missing
    with open("settings.ini", "r") as f:
        current_set = f.read()
    with open("settings.ini", "w") as f:
        f.write(f"[main]\n{current_set}")
    config.read("settings.ini")
try:
    settings = dict(config.items("main"))
except configparser.NoSectionError:  # file missing or header not 'main'
    with open('settings.ini', 'w') as f:
        f.write("""[main]
        default_search_string =  
        default_search_path = C:\\
        search_docx = True
        search_xlsx = True
        search_odt = True
        search_pdf = False
        search_other = True
        logging_enabled = True
        regex_used = True""")
    E_logger.exception("settings file not found or broken. Defaults restored.")
    config.read("settings.ini")
    settings = dict(config.items("main"))

try:
    Default_Search_String = settings["default_search_string"]
    Default_Search_Path = settings["default_search_path"]
    if settings["search_other"] == "True":
        Search_other = True
    else:
        Search_other = False
    if settings["search_docx"] == "True":
        Search_docx = True
    else:
        Search_docx = False
    if settings["search_xlsx"] == "True":
        Search_xlsx = True
    else:
        Search_xlsx = False
    if settings["search_odt"] == "True":
        Search_odt = True
    else:
        Search_odt = False
    if settings["search_pdf"] == "True":
        Search_pdf = True
    else:
        Search_pdf = False
    if settings["logging_enabled"] == "True":
        Logging_enabled = True
    else:
        Logging_enabled = False
    if settings["regex_used"] == "True":
        Regex_used = True
    else:
        Regex_used = False
except KeyError:
    E_logger.exception("missing key.")  # no auto restore for keys


# PyQt5 GUI, mostly code generated by PyQt5 UI code generator:
class Ui_MainWindow(object):
    # add timer for updates:
    def __init__(self):
        super().__init__()
        # timer to update labels and results list
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(500)

        # timer to scale widgets to window size
        self.timer2 = QtCore.QTimer()
        self.timer2.timeout.connect(self.adjust_sizes)
        self.timer2.start(100)

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("TextFinder")
        MainWindow.resize(770, 620)
        MainWindow.setMinimumWidth(740)
        MainWindow.setMinimumHeight(300)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.stop_button = QtWidgets.QPushButton(self.centralwidget)
        self.stop_button.setGeometry(QtCore.QRect(630, 80, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.stop_button.setFont(font)
        self.stop_button.setObjectName("stop_button")
        self.start_button = QtWidgets.QPushButton(self.centralwidget)
        self.start_button.setGeometry(QtCore.QRect(630, 40, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.start_button.setFont(font)
        self.start_button.setObjectName("start_button")
        self.search_text_entry = QtWidgets.QLineEdit(self.centralwidget)
        self.search_text_entry.setGeometry(QtCore.QRect(110, 40, 501, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.search_text_entry.setFont(font)
        self.search_text_entry.setDragEnabled(True)
        self.search_text_entry.setObjectName("search_text_entry")
        self.search_text_entry.setText(Default_Search_String)
        self.search_text_entry.setFocus()
        self.search_dir_entry = QtWidgets.QLineEdit(self.centralwidget)
        self.search_dir_entry.setGeometry(QtCore.QRect(110, 80, 501, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.search_dir_entry.setFont(font)
        self.search_dir_entry.setDragEnabled(True)
        self.search_dir_entry.setObjectName("search_dir_entry")
        self.search_dir_entry.setText(Default_Search_Path)
        self.search_for_label = QtWidgets.QLabel(self.centralwidget)
        self.search_for_label.setGeometry(QtCore.QRect(20, 45, 81, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.search_for_label.setFont(font)
        self.search_for_label.setObjectName("search_for_label")
        self.search_in_label = QtWidgets.QLabel(self.centralwidget)
        self.search_in_label.setGeometry(QtCore.QRect(20, 85, 81, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.search_in_label.setFont(font)
        self.search_in_label.setObjectName("search_in_label")
        self.file_types_label = QtWidgets.QLabel(self.centralwidget)
        self.file_types_label.setGeometry(QtCore.QRect(20, 10, 81, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.file_types_label.setFont(font)
        self.file_types_label.setObjectName("file_types_label")
        self.check_docx = QtWidgets.QCheckBox(self.centralwidget)
        self.check_docx.setEnabled(True)
        self.check_docx.setGeometry(QtCore.QRect(110, 10, 70, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.check_docx.setFont(font)
        self.check_docx.setChecked(Search_docx)
        self.check_docx.setObjectName("check_docx")
        self.check_xlsx = QtWidgets.QCheckBox(self.centralwidget)
        self.check_xlsx.setEnabled(True)
        self.check_xlsx.setGeometry(QtCore.QRect(170, 10, 70, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.check_xlsx.setFont(font)
        self.check_xlsx.setChecked(Search_xlsx)
        self.check_xlsx.setObjectName("check_xlsx")
        self.check_odt = QtWidgets.QCheckBox(self.centralwidget)
        self.check_odt.setEnabled(True)
        self.check_odt.setGeometry(QtCore.QRect(240, 10, 70, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.check_odt.setFont(font)
        self.check_odt.setChecked(Search_odt)
        self.check_odt.setObjectName("check_odt")
        self.check_pdf = QtWidgets.QCheckBox(self.centralwidget)
        self.check_pdf.setEnabled(True)
        self.check_pdf.setGeometry(QtCore.QRect(300, 10, 91, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.check_pdf.setFont(font)
        self.check_pdf.setChecked(Search_pdf)
        self.check_pdf.setObjectName("check_pdf")
        self.check_other = QtWidgets.QCheckBox(self.centralwidget)
        self.check_other.setEnabled(True)
        self.check_other.setGeometry(QtCore.QRect(400, 10, 81, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.check_other.setFont(font)
        self.check_other.setChecked(Search_other)
        self.check_other.setObjectName("check_other")
        self.results_label = QtWidgets.QLabel(self.centralwidget)
        self.results_label.setGeometry(QtCore.QRect(320, 130, 91, 21))
        font = QtGui.QFont()
        font.setPointSize(18)
        self.results_label.setFont(font)
        self.results_label.setObjectName("results_label")
        self.status_label = QtWidgets.QLabel(self.centralwidget)
        self.status_label.setGeometry(QtCore.QRect(40, 510, 121, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.status_label.setFont(font)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setObjectName("status_label")
        self.status_label_go = QtWidgets.QLabel(self.centralwidget)
        self.status_label_go.setGeometry(QtCore.QRect(40, 540, 121, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.status_label_go.setFont(font)
        self.status_label_go.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label_go.setObjectName("status_label_go")
        self.status_label_queued = QtWidgets.QLabel(self.centralwidget)
        self.status_label_queued.setGeometry(QtCore.QRect(180, 540, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.status_label_queued.setFont(font)
        self.status_label_queued.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label_queued.setObjectName("status_label_queued")
        self.files_to_read_label = QtWidgets.QLabel(self.centralwidget)
        self.files_to_read_label.setGeometry(QtCore.QRect(180, 510, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.files_to_read_label.setFont(font)
        self.files_to_read_label.setAlignment(QtCore.Qt.AlignCenter)
        self.files_to_read_label.setObjectName("files_to_read_label")
        self.status_label_read = QtWidgets.QLabel(self.centralwidget)
        self.status_label_read.setGeometry(QtCore.QRect(290, 540, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.status_label_read.setFont(font)
        self.status_label_read.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label_read.setObjectName("status_label_read")
        self.files_read_label = QtWidgets.QLabel(self.centralwidget)
        self.files_read_label.setGeometry(QtCore.QRect(290, 510, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.files_read_label.setFont(font)
        self.files_read_label.setAlignment(QtCore.Qt.AlignCenter)
        self.files_read_label.setObjectName("files_read_label")
        self.not_readable_label = QtWidgets.QLabel(self.centralwidget)
        self.not_readable_label.setGeometry(QtCore.QRect(510, 510, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.not_readable_label.setFont(font)
        self.not_readable_label.setAlignment(QtCore.Qt.AlignCenter)
        self.not_readable_label.setObjectName("not_readable_label")
        self.status_label_found = QtWidgets.QLabel(self.centralwidget)
        self.status_label_found.setGeometry(QtCore.QRect(400, 540, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.status_label_found.setFont(font)
        self.status_label_found.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label_found.setObjectName("status_label_found")
        self.status_label_not_readable = QtWidgets.QLabel(self.centralwidget)
        self.status_label_not_readable.setGeometry(QtCore.QRect(510, 540, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.status_label_not_readable.setFont(font)
        self.status_label_not_readable.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label_not_readable.setObjectName("status_label_not_readable")
        self.files_found_label = QtWidgets.QLabel(self.centralwidget)
        self.files_found_label.setGeometry(QtCore.QRect(400, 510, 101, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.files_found_label.setFont(font)
        self.files_found_label.setAlignment(QtCore.Qt.AlignCenter)
        self.files_found_label.setObjectName("files_found_label")
        self.results = QtWidgets.QListWidget(self.centralwidget)
        self.results.setGeometry(QtCore.QRect(20, 160, 731, 341))
        self.results.setObjectName("results")
        self.results.setAlternatingRowColors(True)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 813, 21))
        self.menubar.setObjectName("menubar")
        self.MainMenue = QtWidgets.QMenu(self.menubar)
        self.MainMenue.setObjectName("MainMenue")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionSave = QtWidgets.QAction(MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionSave.triggered.connect(self.save_settings)
        self.actionUseRegex = QtWidgets.QAction(MainWindow)
        self.actionUseRegex.setCheckable(True)
        self.actionUseRegex.setChecked(Regex_used)
        self.actionUseRegex.setObjectName("actionSet_regex_usage")
        self.actionUseRegex.triggered.connect(set_regex_usage)
        self.actionEnableLogging = QtWidgets.QAction(MainWindow)
        self.actionEnableLogging.setCheckable(True)
        self.actionEnableLogging.setChecked(Logging_enabled)
        self.actionEnableLogging.setObjectName("actionEnable_Logging")
        self.actionEnableLogging.triggered.connect(set_logging)
        self.actionClearLogs = QtWidgets.QAction(MainWindow)
        self.actionClearLogs.setObjectName("actionClearLogs")
        self.actionClearLogs.triggered.connect(clear_logs)
        self.actionExit = QtWidgets.QAction(MainWindow)
        self.actionExit.setObjectName("actionExit")
        self.actionExit.triggered.connect(self.exit)
        self.actionHelp = QtWidgets.QAction(MainWindow)
        self.actionHelp.setObjectName("actionHelp")
        self.actionHelp.triggered.connect(self.show_help)
        self.actionAbout = QtWidgets.QAction(MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.actionAbout.triggered.connect(self.show_about)
        self.MainMenue.addAction(self.actionSave)
        self.MainMenue.addAction(self.actionUseRegex)
        self.MainMenue.addAction(self.actionEnableLogging)
        self.MainMenue.addAction(self.actionClearLogs)
        self.MainMenue.addAction(self.actionExit)
        self.menuHelp.addAction(self.actionHelp)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.MainMenue.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # add functions
        self.start_button.clicked.connect(
            lambda: self.start_search(self.search_dir_entry.text(),
                                      self.search_text_entry.text()))
        self.start_button.setShortcut("Return")
        self.stop_button.clicked.connect(lambda: stop_search())
        self.stop_button.setShortcut("Escape")

        self.update()
        self.adjust_sizes()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", f"TextFinder v{Version}"))
        self.stop_button.setText(_translate("MainWindow", "Stop"))
        self.start_button.setText(_translate("MainWindow", "Search"))
        self.search_for_label.setText(_translate("MainWindow", "Search for:"))
        self.search_in_label.setText(_translate("MainWindow", "Search in:"))
        self.file_types_label.setText(_translate("MainWindow", "File types:"))
        self.check_other.setText(_translate("MainWindow", "other"))
        self.check_docx.setText(_translate("MainWindow", "docx"))
        self.check_xlsx.setText(_translate("MainWindow", "xls(x)"))
        self.check_odt.setText(_translate("MainWindow", "odt"))
        self.check_pdf.setText(_translate("MainWindow", "pdf (slow!)"))
        self.results_label.setText(_translate("MainWindow", "Results:"))
        self.status_label.setText(_translate("MainWindow", "Status:"))
        self.status_label_go.setText(_translate("MainWindow", "Idle"))
        self.status_label_queued.setText(_translate("MainWindow", "0"))
        self.files_to_read_label.setText(_translate("MainWindow", "Files to read:"))
        self.status_label_read.setText(_translate("MainWindow", "0"))
        self.files_read_label.setText(_translate("MainWindow", "Files read:"))
        self.not_readable_label.setText(_translate("MainWindow", "Not readable:"))
        self.status_label_found.setText(_translate("MainWindow", "0"))
        self.status_label_not_readable.setText(_translate("MainWindow", "0"))
        self.files_found_label.setText(_translate("MainWindow", "Files found:"))
        __sortingEnabled = self.results.isSortingEnabled()
        self.results.setSortingEnabled(False)
        self.results.setSortingEnabled(__sortingEnabled)
        self.MainMenue.setTitle(_translate("MainWindow", "File"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.actionExit.setText(_translate("MainWindow", "Exit"))
        self.actionSave.setText(_translate("MainWindow", "Save Settings"))
        self.actionEnableLogging.setText(_translate("MainWindow", "Enable Logging"))
        self.actionUseRegex.setText(_translate("MainWindow", "Use Regular Expressions"))
        self.actionClearLogs.setText(_translate("MainWindow", "Clear Logs"))
        self.actionHelp.setText(_translate("MainWindow", "Help"))
        self.actionAbout.setText(_translate("MainWindow", "About"))

    def adjust_sizes(self):
        """updates the size of the results list
        and the position of the status labels
        """
        main_width = MainWindow.width()
        main_height = MainWindow.height()

        if self.results.width() != main_width - 40 or\
                self.results.height() != main_height - 280:
            self.results.setFixedWidth(int(main_width - 40))
            self.results.setFixedHeight(main_height - 280)
            res_label_x = int(self.results.width() / 2 - self.results_label.width() / 2)
            self.results_label.setGeometry(QtCore.QRect(res_label_x, 130, 91, 21))

            # adjust height of labels:
            results_bottom = self.results.y() + self.results.height()
            self.status_label.setGeometry(QtCore.QRect(40, results_bottom + 10, 121, 21))
            self.status_label_go.setGeometry(QtCore.QRect(40, results_bottom + 40, 121, 21))
            self.status_label_queued.setGeometry(QtCore.QRect(180, results_bottom + 40, 101, 21))
            self.files_to_read_label.setGeometry(QtCore.QRect(180, results_bottom + 10, 101, 21))
            self.status_label_read.setGeometry(QtCore.QRect(290, results_bottom + 40, 101, 21))
            self.files_read_label.setGeometry(QtCore.QRect(290, results_bottom + 10, 101, 21))
            self.not_readable_label.setGeometry(QtCore.QRect(510, results_bottom + 10, 101, 21))
            self.status_label_found.setGeometry(QtCore.QRect(400, results_bottom + 40, 101, 21))
            self.status_label_not_readable.setGeometry(QtCore.QRect(510, results_bottom + 40, 101, 21))
            self.files_found_label.setGeometry(QtCore.QRect(400, results_bottom + 10, 101, 21))

    def update(self):
        """Updates the text of the status labels."""
        self.status_label_go.setText(Status_Text)
        self.status_label_queued.setText(str(Files_queued))
        self.status_label_read.setText(str(Files_read))
        self.status_label_found.setText(str(Files_found))
        self.status_label_not_readable.setText(str(Files_not_readable))
        while not Output_queue.empty():
            self.results.addItem(str(Output_queue.get()))

    def start_search(self, path, search_string):
        """Clear old results, possibly files queued for reading and
        reset global counters / variables. Then start two threads:
        1. Queue files in the folder and subfolders.
        2. Call the queue_handler to call the read functions for
        each queue if it is not empty until all files are read.
        """
        # clear old results, possibly files queued for reading
        # and reset global counters / variables:
        self.results.clear()
        Other_queue.queue.clear()
        Docx_queue.queue.clear()
        Xlsx_queue.queue.clear()
        Odt_queue.queue.clear()
        Pdf_queue.queue.clear()

        # reset global variables that are used for the status labels
        global Files_queued, Files_read, Files_found, Files_not_readable, \
            Queueing_done, Queue_handler_done, Status_Text
        Files_queued = 0
        Files_read = 0
        Files_found = 0
        Files_not_readable = 0

        # for starting new search:
        Queueing_done = False
        Queue_handler_done = False
        Status_Text = "Searching"

        # start two threads:
        # 1. Queue files in the folder and subfolders
        # 2. Call the queue_handler to call the read functions for
        # each queue if it is not empty until all files are read:
        file_thread = threading.Thread(target=self.get_files, args=(path,))
        file_thread.daemon = True
        file_thread.start()

        queue_handler_thread = threading.Thread(
            target=self.queue_handler, args=(search_string,))
        queue_handler_thread.daemon = True
        queue_handler_thread.start()

    def get_files(self, search_path):
        """get all files in specified path and add them
        to the file type specific queue.
        """
        global Files_queued, Queueing_done
        start_time = time.perf_counter()
        if os.path.exists(search_path):
            for root, dirs, files in os.walk(search_path, topdown=False):
                if not Stop_pressed:
                    for name in files:
                        file = os.path.join(root, name)
                        if file.lower().endswith(".docx") \
                                and self.check_docx.isChecked():
                            Docx_queue.put(file)
                            Files_queued += 1
                        elif file.lower().endswith(".xlsx") \
                                and self.check_xlsx.isChecked():
                            Xlsx_queue.put(file)
                            Files_queued += 1
                        elif file.lower().endswith(".xls") \
                                and self.check_xlsx.isChecked():
                            Xlsx_queue.put(file)
                            Files_queued += 1
                        elif file.lower().endswith(".odt") \
                                and self.check_odt.isChecked():
                            Odt_queue.put(file)
                            Files_queued += 1
                        elif file.lower().endswith(".pdf") \
                                and self.check_pdf.isChecked():
                            Pdf_queue.put(file)
                            Files_queued += 1
                        elif not file.lower().endswith(skipped_types) \
                                and self.check_other.isChecked():
                            Other_queue.put(file)
                            Files_queued += 1
                else:
                    break
            Queueing_done = True
            end_time = time.perf_counter()
            queue_time = end_time - start_time
            # print(f"get_files done, queued {counter} files in {queue_time} seconds")
        else:
            Queueing_done = True
            Output_queue.put(f"Directory '{search_path}' does not exist!")

    @staticmethod
    def queue_handler(search_string):
        """call the read functions for each queue if it is not empty until
        all files are read or Stop is pressed.
        """
        global Queue_handler_done, Status_Text
        start_time = time.perf_counter()
        while True:
            if not Stop_pressed:
                if not Other_queue.empty():
                    other_text_search(search_string)
                elif not Docx_queue.empty():
                    word_search(search_string)
                elif not Xlsx_queue.empty():
                    excel_search(search_string)
                elif not Odt_queue.empty():
                    odt_search(search_string)
                elif not Pdf_queue.empty():
                    pdf_search(search_string)
                elif Queueing_done and Files_read == Files_queued:
                    break
            else:
                break
        Queue_handler_done = True
        end_time = time.perf_counter()
        search_time = end_time - start_time
        Status_Text = "Search complete"
        # print(f"Search done, read {Files_read} files in"
        #      f" {search_time} seconds. Errors: {Files_not_readable}")

    def save_settings(self):
        """Save current settings to ini file."""
        config.set("main", "search_docx", str(self.check_docx.isChecked()))
        config.set("main", "search_xlsx", str(self.check_xlsx.isChecked()))
        config.set("main", "search_odt", str(self.check_odt.isChecked()))
        config.set("main", "search_pdf", str(self.check_pdf.isChecked()))
        config.set("main", "search_other", str(self.check_other.isChecked()))
        config.set('main', 'default_search_string', self.search_text_entry.text())
        config.set('main', 'default_search_path', self.search_dir_entry.text())
        with open('settings.ini', 'w') as sf:
            config.write(sf)

    def show_help(self):
        """Open the help window."""
        self.help_dialog = QtWidgets.QDialog(MainWindow)  # MainWindow as parent so this closes too
        self.ui = Ui_help_dialog()
        self.ui.setupUi(self.help_dialog)
        self.help_dialog.show()

    def show_about(self):
        """Open the about window."""
        self.about_dialog = QtWidgets.QDialog(MainWindow)
        self.ui = Ui_about_dialog()
        self.ui.setupUi(self.about_dialog)
        self.about_dialog.show()

    def exit(self):
        """Exit the program."""
        sys.exit(app.exec_())


def stop_search():
    """Stop search by changing the global var to True.
     When threads are done, reset stop variable to allow for a new search.
     """
    global Stop_pressed
    if not Stop_pressed:
        Stop_pressed = True
        while True:
            if Queueing_done and Queue_handler_done:
                Stop_pressed = False
                break
            else:
                time.sleep(0.1)


def set_logging():
    """Turn logging on or off."""
    global Logging_enabled
    if Logging_enabled:
        Logging_enabled = False
    else:
        Logging_enabled = True
    config.set("main", "Logging_enabled", str(Logging_enabled))
    with open('settings.ini', 'w') as f:
        config.write(f)


def set_regex_usage():
    """Turn Regex usage on or off."""
    global Regex_used
    if Regex_used:
        Regex_used = False
    else:
        Regex_used = True
    config.set("main", "regex_used", str(Regex_used))
    with open('settings.ini', 'w') as f:
        config.write(f)


def clear_logs():
    """Delete all content from the log files."""
    with open("Info.log", "w") as E_file:
        E_file.write("")
    with open("Error.log", "w") as E_file:
        E_file.write("")


def word_search(search_string):
    """search for a given string in a specific MS Word docx file.
    Does not work with .doc.
    """
    global Files_not_readable, Files_read, Files_found
    search_expr = re.compile(search_string)
    while not Docx_queue.empty():
        if not Stop_pressed:
            file = Docx_queue.get()
            Files_read += 1
            try:
                if Regex_used:
                    if search_expr.search(docx2txt.process(file)) is not None:
                        Output_queue.put(file)
                        Files_found += 1
                        return True
                    else:
                        return False
                else:
                    if search_string in docx2txt.process(file):
                        Output_queue.put(file)
                        Files_found += 1
                        return True
                    else:
                        return False
            except BaseException:
                Files_not_readable += 1
                E_logger.exception(f"Error reading {file}")
                return False


def excel_search(search_string):
    """search for a given string in a specific MS Excel file."""
    global Files_not_readable, Files_read, Files_found
    search_expr = re.compile(search_string)
    while not Xlsx_queue.empty():
        if not Stop_pressed:
            file = Xlsx_queue.get()
            Files_read += 1
            try:
                excel_data = pd.read_excel(file)
                for index, rows in excel_data.iterrows():
                    if Regex_used:
                        if search_expr.search(rows.to_string()) is not None:
                            Output_queue.put(file)
                            Files_found += 1
                            return True
                        else:
                            return False
                    else:
                        if search_string in rows.to_string():
                            Output_queue.put(file)
                            Files_found += 1
                            return True
                        else:
                            return False
            except BaseException:
                Files_not_readable += 1
                E_logger.exception(f"Error reading {file}")
                return False


def odt_search(search_string):
    """search for a given string in a specific open office text file."""
    global Files_not_readable, Files_read, Files_found
    search_expr = re.compile(search_string)
    while not Odt_queue.empty():
        if not Stop_pressed:
            file = Odt_queue.get()
            Files_read += 1
            try:
                odtfile = load(file)
                odt_content = odtfile.getElementsByType(text.P)
                for n in range(len(odt_content)):
                    odt_text = teletype.extractText(odt_content[n])
                    if Regex_used:
                        if search_expr.search(odt_text) is not None:
                            Output_queue.put(file)
                            Files_found += 1
                            return True
                    else:
                        if search_string in odt_text:
                            Output_queue.put(file)
                            Files_found += 1
                            return True
                return False
            except BaseException:
                Files_not_readable += 1
                E_logger.exception(f"Error reading {file}")
                return False


def pdf_search(search_string):
    """search for a given string in a specific pdf file using pdf miner.
    This is very slow!
    """
    global Files_not_readable, Files_read, Files_found
    search_expr = re.compile(search_string)
    while not Pdf_queue.empty():
        if not Stop_pressed:
            file = Pdf_queue.get()
            rsrcmgr = PDFResourceManager()
            retstr = StringIO()
            codec = 'utf-8'
            laparams = LAParams()
            device = TextConverter(rsrcmgr, retstr, laparams=laparams)
            fp = open(file, 'rb')
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            password = ""
            maxpages = 0
            caching = True
            pagenos = set()
            try:
                for page in PDFPage.get_pages(fp, pagenos,
                                              maxpages=maxpages,
                                              password=password,
                                              caching=caching,
                                              check_extractable=True):
                    interpreter.process_page(page)
                pdf_text = retstr.getvalue()
                fp.close()
                device.close()
                retstr.close()
                if Regex_used:
                    if search_expr.search(pdf_text) is not None:
                        Output_queue.put(file)
                        Files_found += 1
                else:
                    if search_string in pdf_text:
                        Output_queue.put(file)
                        Files_found += 1
                Files_read += 1

            except BaseException:
                Files_not_readable += 1
                E_logger.exception(f"Error reading {file}")


def other_text_search(search_string):
    """search for a given string in the OS-standard encoding
    (cp1252 on windows) or utf-8 encoded file.
    """
    global Files_not_readable, Files_read, Files_found
    search_expr = re.compile(search_string)
    while not Other_queue.empty():
        if not Stop_pressed:
            file = Other_queue.get()
            Files_read += 1
            try:
                with open(file) as current_file:
                    # print(f"coding for txt: {locale.getpreferredencoding()}")
                    if Regex_used:
                        if search_expr.search(current_file.read()) is not None:
                            Output_queue.put(file)
                            Files_found += 1
                            return True
                        else:
                            with io.open(file, encoding="utf-8") as file_utf:
                                if search_expr.search(file_utf.read()) is not None:
                                    Output_queue.put(file)
                                    Files_found += 1
                                    return True
                                else:
                                    return False
                    else:
                        if search_string in current_file.read():
                            Output_queue.put(file)
                            Files_found += 1
                            return True
                        else:
                            with io.open(file, encoding="utf-8") as file_utf:
                                if search_string in file_utf.read():
                                    Output_queue.put(file)
                                    Files_found += 1
                                    return True
                                else:
                                    return False
            except BaseException:
                Files_not_readable += 1
                I_logger.info(f"Not readable as text: {file}")  # no error - file may be non-text
                return False


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
