# -*- coding: utf-8 -*-
"""
main_window.py - Main application window for Excel to DBC to C Toolchain
"""
import os
import sys
import json
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QSplitter, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QStatusBar, QProgressBar,
    QFrame, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.tabs import ExcelTab, DbcTab, CodeTab
from ui.visualizer_tab import VisualizerTab


# ─────────────────────────────────────────────────────────────
# Worker thread – runs a subprocess without blocking the GUI
# ─────────────────────────────────────────────────────────────
class PipelineWorker(QThread):
    """Runs a pipeline step in a background thread."""
    progress = pyqtSignal(int)
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, cmd, step_label):
        super().__init__()
        self._cmd = cmd
        self._step_label = step_label

    def run(self):
        self.progress.emit(10)
        try:
            proc = subprocess.Popen(
                self._cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stdout:
                self.log.emit(line.rstrip())
            proc.wait()
            self.progress.emit(100)
            if proc.returncode == 0:
                self.finished.emit(True,  self._step_label + " completed successfully.")
            else:
                self.finished.emit(False, self._step_label + " failed (exit code {}).".format(proc.returncode))
        except Exception as e:
            self.progress.emit(0)
            self.finished.emit(False, str(e))


# ─────────────────────────────────────────────────────────────
# Sidebar / Project Explorer
# ─────────────────────────────────────────────────────────────
class SidebarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        hdr = QLabel("Project Explorer")
        hdr.setObjectName("sidebarHeader")
        layout.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #CBD5E1;")
        layout.addWidget(sep)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        layout.addWidget(self.tree, 1)

        root_item = QTreeWidgetItem(self.tree, ["CAN Toolchain"])
        root_item.setExpanded(True)

        self._input_item = QTreeWidgetItem(root_item, ["[1] Input Excel"])
        self._dbc_item   = QTreeWidgetItem(root_item, ["[2] DBC File"])
        self._code_item  = QTreeWidgetItem(root_item, ["[3] C / H Code"])

        self.set_step_status(0, "pending")
        self.set_step_status(1, "pending")
        self.set_step_status(2, "pending")

    def set_step_status(self, step, status):
        """status: 'pending' | 'running' | 'done' | 'error'"""
        items = [self._input_item, self._dbc_item, self._code_item]
        labels = [
            ("[1] Input Excel",  "[..] Input Excel",  "[OK] Input Excel",  "[!] Input Excel"),
            ("[2] DBC File",     "[..] DBC File",     "[OK] DBC File",     "[!] DBC File"),
            ("[3] C / H Code",   "[..] C / H Code",   "[OK] C / H Code",   "[!] C / H Code"),
        ]
        colours = {"pending": "#64748B", "running": "#2563EB", "done": "#16A34A", "error": "#DC2626"}
        idx = {"pending": 0, "running": 1, "done": 2, "error": 3}.get(status, 0)
        items[step].setText(0, labels[step][idx])
        items[step].setForeground(0, QColor(colours.get(status, "#64748B")))


# ─────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    TAB_EXCEL = 0
    TAB_DBC   = 1
    TAB_CODE  = 2

    def __init__(self):
        super().__init__()
        self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._config   = self._load_config()
        self._worker   = None
        self._is_exporting_all = False
        self._export_step = 1
        self._setup_window()
        self._build_ui()
        self._apply_theme()
        self._preload_paths()

    # ── Config ──────────────────────────────────────────────────
    def _load_config(self):
        path = os.path.join(self._base_dir, "config.json")
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    # ── Window setup ────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowTitle("Excel to DBC to C Toolchain")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

    # ── Theme ───────────────────────────────────────────────────
    def _apply_theme(self):
        qss_path = os.path.join(self._base_dir, "ui", "theme.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    # ── UI construction ─────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Top toolbar ────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #CBD5E1;")
        toolbar.setFixedHeight(52)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)

        app_label = QLabel("Excel to DBC to C Toolchain")
        app_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #1E293B;")
        toolbar_layout.addWidget(app_label)
        toolbar_layout.addStretch(1)

        self.export_btn = QPushButton("Export Toolchain")
        self.export_btn.setObjectName("PrimaryButton")
        self.export_btn.setMinimumWidth(160)
        self.export_btn.clicked.connect(self._run_export_toolchain)
        toolbar_layout.addWidget(self.export_btn)

        main_layout.addWidget(toolbar)

        # ── Content area ────────────────────────────────────────
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.sidebar.setStyleSheet("background: #F1F5F9; border-right: 1px solid #CBD5E1;")
        content_layout.addWidget(self.sidebar)

        # ── Tab widget ──────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.excel_tab = ExcelTab()
        self.dbc_tab   = DbcTab()
        
        self.dbc_tab.export_excel_requested.connect(self._run_dbc_to_excel)
        self.dbc_tab.generate_code_requested.connect(self._run_generate_code)
        self.dbc_tab.load_dbc_requested.connect(self._on_dbc_loaded_manually)
        
        self.code_tab  = CodeTab()
        self.visualizer_tab = VisualizerTab()

        self.excel_tab.visualizer_update_requested.connect(self.visualizer_tab.update_visualizer)
        self.excel_tab.visualizer_matrix_updated.connect(self.visualizer_tab.set_available_messages)

        self.tabs.addTab(self.excel_tab, "Excel Input")
        self.tabs.addTab(self.visualizer_tab, "CAN Visualizer")
        self.tabs.addTab(self.dbc_tab,  "DBC Review")
        self.tabs.addTab(self.code_tab, "C / H Output")

        content_layout.addWidget(self.tabs, 1)
        main_layout.addWidget(content, 1)

        # ── Status bar ──────────────────────────────────────────
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._status_label = QLabel("Ready.")
        self._status_bar.addWidget(self._status_label, 1)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(300)
        self._progress.setFixedHeight(10)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress)

        # ── Menu bar ────────────────────────────────────────────
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        open_action = file_menu.addAction("Open Excel ...")
        open_action.triggered.connect(self._open_excel_from_menu)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        help_menu = menu_bar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._show_about)

    # ── Pre-load config paths ────────────────────────────────────
    def _preload_paths(self):
        excel_rel = self._config.get("excel_file", "")
        if excel_rel:
            excel_abs = os.path.join(self._base_dir, excel_rel)
            self.excel_tab.load_from_path(excel_abs)
            if os.path.exists(excel_abs):
                self.sidebar.set_step_status(0, "done")

        dbc_rel = self._config.get("dbc_output", "output/dbc/generated.dbc")
        if dbc_rel:
            dbc_abs = os.path.join(self._base_dir, dbc_rel)
            self.dbc_tab.load_dbc(dbc_abs)
            if os.path.exists(dbc_abs):
                self.sidebar.set_step_status(1, "done")

        c_rel = self._config.get("c_output_dir", "output/c_code")
        if c_rel:
            c_abs = os.path.join(self._base_dir, c_rel)
            self.code_tab.load_output_dir(c_abs)
            if os.path.isdir(c_abs) and any(f.endswith(".c") for f in os.listdir(c_abs)):
                self.sidebar.set_step_status(2, "done")

    # ── Tab changed ──────────────────────────────────────────────
    def _on_tab_changed(self, index):
        pass

    # ── Export Toolchain ─────────────────────────────────────────
    def _run_export_toolchain(self):
        self._is_exporting_all = True
        self._export_step = 1
        self._run_excel_to_dbc(on_success_override=self._export_step_1_success)

    def _export_step_1_success(self, dbc_abs):
        self._after_dbc_generated(dbc_abs)
        self._export_step = 2
        
        # We need DBC to be generated completely before running step 2. 
        # C_Output dir logic uses DBC path from tab.
        # It's better to queue it with a tiny delay so the UI thread breathes
        QTimer.singleShot(100, lambda: self._run_generate_code(on_success_override=self._export_step_2_success))

    def _export_step_2_success(self, c_abs):
        self._after_code_generated(c_abs)
        self._is_exporting_all = False
        self._set_status("Full toolchain export completed successfully.")
        
    def _run_dbc_to_excel(self, dbc_path):
        if not dbc_path or not os.path.exists(dbc_path):
            return
            
        base_name = os.path.splitext(os.path.basename(dbc_path))[0]
        excel_out_rel = f"output/excel/{base_name}.xlsx"
        excel_out = os.path.join(self._base_dir, excel_out_rel)
        os.makedirs(os.path.dirname(excel_out), exist_ok=True)

        script = os.path.join(self._base_dir, "scripts", "dbc_to_excel.py")
        cmd = [sys.executable, script, dbc_path, excel_out]

        self._start_worker(cmd, "DBC to Excel Reverse Engineering", step=0,
                           on_success=lambda: self._after_dbc_exported(excel_out))

    def _after_dbc_exported(self, excel_out):
        self.tabs.setCurrentIndex(self.TAB_EXCEL)
        self.excel_tab.load_from_path(excel_out)
        self.sidebar.set_step_status(0, "done")
        QMessageBox.information(self, "Success", f"DBC reversed and Excel matrix fully loaded!\nSaved to: {excel_out}")

    def _on_dbc_loaded_manually(self, dbc_path):
        self.sidebar.set_step_status(1, "done")

    # ── Step 1: Excel to DBC ─────────────────────────────────────
    def _run_excel_to_dbc(self, on_success_override=None):
        excel_path = self.excel_tab.get_excel_path()
        if not excel_path or not os.path.exists(excel_path):
            QMessageBox.warning(self, "No Excel File",
                                "Please select a valid Excel file on the Excel Input tab.")
            return

        dbc_rel = self._config.get("dbc_output", "output/dbc/generated.dbc")
        dbc_abs = os.path.join(self._base_dir, dbc_rel)
        os.makedirs(os.path.dirname(dbc_abs), exist_ok=True)

        script = os.path.join(self._base_dir, "scripts", "excel_to_dbc.py")
        cmd = [sys.executable, script, excel_path, dbc_abs]

        success_callback = on_success_override if on_success_override else lambda: self._after_dbc_generated(dbc_abs)
        # We need to wrap it if it requires args
        if on_success_override:
            success_callback = lambda: on_success_override(dbc_abs)

        self._start_worker(cmd, "DBC Generation", step=1,
                           on_success=success_callback)

    def _after_dbc_generated(self, dbc_abs):
        self.sidebar.set_step_status(1, "done")
        self.dbc_tab.load_dbc(dbc_abs)
        self.tabs.setCurrentIndex(self.TAB_DBC)

    # ── Step 2: DBC to C/H ───────────────────────────────────────
    def _run_generate_code(self, on_success_override=None):
        dbc_path = self.dbc_tab.get_dbc_path()
        if not dbc_path or not os.path.exists(dbc_path):
            QMessageBox.warning(self, "No DBC File", "Generate the DBC file first (Step 1).")
            return

        c_rel = self._config.get("c_output_dir", "output/c_code")
        c_abs = os.path.join(self._base_dir, c_rel)
        os.makedirs(c_abs, exist_ok=True)

        script = os.path.join(self._base_dir, "scripts", "generate_code.py")
        cmd = [sys.executable, script, dbc_path, c_abs]

        success_callback = on_success_override if on_success_override else lambda: self._after_code_generated(c_abs)
        if on_success_override:
            success_callback = lambda: on_success_override(c_abs)

        self._start_worker(cmd, "C/H Code Generation", step=2,
                           on_success=success_callback)

    def _after_code_generated(self, c_abs):
        self.sidebar.set_step_status(2, "done")
        self.code_tab.load_output_dir(c_abs)
        self.tabs.setCurrentIndex(self.TAB_CODE)

    # ── Refresh code tab ─────────────────────────────────────────
    def _refresh_code_tab(self):
        c_rel = self._config.get("c_output_dir", "output")
        c_abs = os.path.join(self._base_dir, c_rel)
        self.code_tab.load_output_dir(c_abs)
        self._set_status("Output refreshed.")

    # ── Worker helper ────────────────────────────────────────────
    def _start_worker(self, cmd, label, step, on_success=None):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Busy", "A pipeline step is already running.")
            return

        self.export_btn.setEnabled(False)
        self._progress.setVisible(True)
        if not self._is_exporting_all or self._export_step == 1:
            self._progress.setValue(10)
        self.sidebar.set_step_status(step, "running")
        self._set_status(label + "... Status in Progress")

        self._worker = PipelineWorker(cmd, label)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.log.connect(lambda msg: self._set_status(msg))
        self._worker.finished.connect(
            lambda ok, msg: self._on_worker_finished(ok, msg, step, on_success)
        )
        self._worker.start()

    def _on_worker_progress(self, val):
        if self._is_exporting_all:
            if self._export_step == 1:
                self._progress.setValue(int(val * 0.5))
            elif self._export_step == 2:
                self._progress.setValue(50 + int(val * 0.5))
        else:
            self._progress.setValue(val)

    def _on_worker_finished(self, success, msg, step, on_success):
        if not (self._is_exporting_all and success and step == 1):
            self.export_btn.setEnabled(True)

        if success:
            self._set_status(msg)
            if on_success:
                on_success()
        else:
            self.sidebar.set_step_status(step, "error")
            self._set_status("Error: " + msg)
            QMessageBox.critical(self, "Pipeline Error", msg)
            self._is_exporting_all = False

        if not (self._is_exporting_all and success and step == 1):
            self._progress.setValue(100 if success else 0)
            QTimer.singleShot(2000, lambda: self._progress.setVisible(False))

    def _set_status(self, msg):
        self._status_label.setText(msg)

    # ── Menu actions ─────────────────────────────────────────────
    def _open_excel_from_menu(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self.tabs.setCurrentIndex(self.TAB_EXCEL)
            self.excel_tab.load_from_path(path)
            self.sidebar.set_step_status(0, "done")

    def _show_about(self):
        QMessageBox.about(
            self,
            "About",
            "<b>Excel to DBC to C Toolchain</b><br>"
            "A graphical pipeline tool for CAN matrix conversion.<br><br>"
            "Steps:<br>"
            "1. Load Excel CAN matrix<br>"
            "2. Generate .dbc file<br>"
            "3. Generate C/H source code"
        )
