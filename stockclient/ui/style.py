"""Application style sheets (dark / light), matching the design document."""

from __future__ import annotations

DARK = """
QWidget { background:#1b1e24; color:#c8ccd4; font-size:13px; }
QMainWindow::separator { background:#2a2f38; width:1px; height:1px; }
QToolBar, QToolButton, QStatusBar { background:#222630; }
QToolButton:hover { background:#2f3542; border-radius:4px; }
QToolButton:checked { background:#3a4250; border-radius:4px; }
QLineEdit, QComboBox, QSpinBox {
    background:#161920; border:1px solid #333a46; border-radius:4px; padding:3px 6px; }
QLineEdit:focus, QComboBox:focus { border-color:#4aa3ff; }
QHeaderView::section { background:#222630; border:0; padding:4px; }
QTableWidget, QTreeWidget { background:#1b1e24; gridline-color:#2a2f38; border:0; }
QTableWidget::item:selected, QTreeWidget::item:selected { background:#2f3542; }
QDockWidget::title { background:#222630; padding:5px; }
"""

LIGHT = """
QWidget { background:#f5f6f8; color:#1f2430; font-size:13px; }
QToolBar, QToolButton, QStatusBar { background:#e9ebf0; }
QToolButton:hover { background:#dfe3ea; border-radius:4px; }
QToolButton:checked { background:#cdd4e0; border-radius:4px; }
QLineEdit, QComboBox, QSpinBox {
    background:#ffffff; border:1px solid #c6ccd8; border-radius:4px; padding:3px 6px; }
QLineEdit:focus, QComboBox:focus { border-color:#2f7fe0; }
QHeaderView::section { background:#e9ebf0; border:0; padding:4px; }
QTableWidget, QTreeWidget { background:#ffffff; gridline-color:#e2e6ee; border:0; }
QTableWidget::item:selected, QTreeWidget::item:selected { background:#d7e3f7; }
QDockWidget::title { background:#e9ebf0; padding:5px; }
"""


def sheet(theme: str) -> str:
    return LIGHT if theme == "light" else DARK
