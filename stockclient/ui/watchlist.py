"""Left dock: 分组 tree + 自选股 list (design document region 2)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)

UP, DOWN = QColor("#e2534b"), QColor("#3fb27f")


class WatchlistPanel(QWidget):
    symbolSelected = Signal(str, str)

    HEADERS = ("代码", "名称", "涨跌%")

    def __init__(self, groups: dict[str, list[tuple[str, str]]], parent=None):
        super().__init__(parent)
        title = QLabel("自选股 / 分组")
        title.setStyleSheet("font-weight:600; padding:2px;")

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMaximumHeight(120)
        self.tree.itemClicked.connect(self._on_group)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_row)
        self.table.setColumnWidth(0, 62)
        self.table.setColumnWidth(2, 62)

        add = QPushButton("+ 添加")
        remove = QPushButton("- 删除")
        add.clicked.connect(self._add_symbol)
        remove.clicked.connect(self._remove_symbol)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(remove)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(title)
        lay.addWidget(self.tree)
        lay.addWidget(self.table, 1)
        lay.addLayout(buttons)

        self._rows: dict[str, int] = {}
        self.groups = groups
        self.populate()

    # -- data --------------------------------------------------------------
    def populate(self) -> None:
        self.tree.clear()
        self.groups["持仓"] = self.groups.get("持仓", [])
        for name, members in self.groups.items():
            node = QTreeWidgetItem([f"{name}  ({len(members)})"])
            node.setData(0, Qt.UserRole, name)
            self.tree.addTopLevelItem(node)
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
            self.set_group(self.tree.topLevelItem(0).data(0, Qt.UserRole))

    def set_group(self, name: str) -> None:
        members = self.groups.get(name, [])
        self.table.setRowCount(len(members))
        self._rows.clear()
        for r, (code, stock_name) in enumerate(members):
            self._rows[code] = r
            self.table.setItem(r, 0, QTableWidgetItem(code))
            self.table.setItem(r, 1, QTableWidgetItem(stock_name))
            self.table.setItem(r, 2, QTableWidgetItem("—"))

    def update_quote(self, quote) -> None:
        r = self._rows.get(quote.code)
        if r is None:
            return
        item = self.table.item(r, 2)
        if item is None:
            return
        item.setText(f"{quote.pct:+.2f}")
        item.setForeground(UP if quote.pct >= 0 else DOWN)
        name = self.table.item(r, 1)
        if name and quote.name:
            name.setText(quote.name)

    # -- events ------------------------------------------------------------
    def _on_group(self, item: QTreeWidgetItem, _col: int) -> None:
        self.set_group(item.data(0, Qt.UserRole))

    def _on_row(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        code = self.table.item(r, 0).text()
        name = self.table.item(r, 1).text()
        self.symbolSelected.emit(code, name)

    def _add_symbol(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        code, ok = QInputDialog.getText(self, "添加自选", "股票代码：")
        if ok and code.strip():
            group = self.tree.currentItem().data(0, Qt.UserRole) if self.tree.currentItem() else "默认"
            self.groups.setdefault(group, []).append((code.strip(), code.strip()))
            self.set_group(group)
            self.populate()

    def _remove_symbol(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        r = rows[0].row()
        code = self.table.item(r, 0).text()
        group = self.tree.currentItem().data(0, Qt.UserRole) if self.tree.currentItem() else "默认"
        self.groups[group] = [m for m in self.groups.get(group, []) if m[0] != code]
        self.set_group(group)
        self.populate()
