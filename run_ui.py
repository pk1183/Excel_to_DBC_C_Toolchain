"""
run_ui.py  –  Entry point for the Excel to DBC to C Toolchain GUI.

Usage:
    python run_ui.py
"""
import sys
import os

# Ensure the project root is on sys.path so `ui` package resolves correctly
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Excel to DBC to C Toolchain")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
