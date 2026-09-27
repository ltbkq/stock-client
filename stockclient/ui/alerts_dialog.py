"""Alert management dialog: list / add / remove / enable-disable rules.

Covers all four rule kinds (价格上穿 / 价格下破 / 涨幅超过 / 跌幅超过).
Self-contained and importable without side effects.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QInputDialog,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..alerts import AlertEngine
from ..models import ALERT_KINDS, Alert

HEADERS = ("类型", "条件", "阈值", "启用", "备注")

# kind -> (字段, 运算符)，用于「条件」列展示
_CONDITIONS = {
    "price_above": ("最新价", "≥"),
    "price_below": ("最新价", "≤"),
    "pct_above": ("涨跌幅", "≥"),
    "pct_below": ("涨跌幅", "≤"),
}


class AlertsDialog(QDialog):
    """管理当前标的的预警规则（列表 / 添加 / 删除 / 启停）。"""

    def __init__(self, engine: AlertEngine, symbol: tuple[str, str], parent=None):
        super().__init__(parent)
        self.engine = engine
        self.code, self.name = symbol

        self.setWindowTitle(f"预警管理 - {self.name} {self.code}")
        self.resize(480, 320)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)

        add_btn = QPushButton("添加")
        del_btn = QPushButton("删除")
        toggle_btn = QPushButton("启停")
        close_btn = QPushButton("关闭")
        add_btn.clicked.connect(self._add)
        del_btn.clicked.connect(self._remove)
        toggle_btn.clicked.connect(self._toggle)
        close_btn.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addWidget(add_btn)
        buttons.addWidget(del_btn)
        buttons.addWidget(toggle_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"{self.name}（{self.code}）"))
        lay.addWidget(self.table, 1)
        lay.addLayout(buttons)

        self._refreshing = False
        self._reload()

    # -- helpers -----------------------------------------------------------
    def _alerts(self) -> list[Alert]:
        return [a for a in self.engine.alerts if a.code == self.code]

    def _reload(self) -> None:
        """重建列表（添加 / 删除 / 启停后调用）。"""
        self._refreshing = True
        alerts = self._alerts()
        self.table.setRowCount(len(alerts))
        for row, alert in enumerate(alerts):
            field, op = _CONDITIONS.get(alert.kind, ("?", "?"))
            self.table.setItem(row, 0, QTableWidgetItem(ALERT_KINDS.get(alert.kind, alert.kind)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{field} {op}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{alert.threshold:g}"))
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            check.setCheckState(Qt.Checked if alert.enabled else Qt.Unchecked)
            self.table.setItem(row, 3, check)
            self.table.setItem(row, 4, QTableWidgetItem(alert.note))
        self._refreshing = False

    def _selected_alert(self) -> Alert | None:
        row = self.table.currentRow()
        alerts = self._alerts()
        if 0 <= row < len(alerts):
            return alerts[row]
        return None

    # -- slots -------------------------------------------------------------
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        # 「启用」列勾选变化 -> 同步 alert.enabled
        if self._refreshing or item.column() != 3:
            return
        alerts = self._alerts()
        if 0 <= item.row() < len(alerts):
            alerts[item.row()].enabled = item.checkState() == Qt.Checked

    def _add(self) -> None:
        kind, ok = QInputDialog.getItem(
            self, "添加预警", "规则类型：", list(ALERT_KINDS.values()), 0, False)
        if not ok:
            return
        key = next(k for k, v in ALERT_KINDS.items() if v == kind)
        unit = "%" if key.startswith("pct") else "元"
        threshold, ok = QInputDialog.getDouble(
            self, "添加预警", f"{kind} 阈值（{unit}）：", 0.0, -1e6, 1e6, 2)
        if ok:
            self.engine.add(Alert(code=self.code, kind=key, threshold=threshold))
            self._reload()

    def _remove(self) -> None:
        alert = self._selected_alert()
        if alert is not None:
            self.engine.remove(alert)
            self._reload()

    def _toggle(self) -> None:
        alert = self._selected_alert()
        if alert is not None:
            alert.enabled = not alert.enabled
            self._reload()
