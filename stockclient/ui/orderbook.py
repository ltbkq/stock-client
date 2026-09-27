"""Right dock: 盘口五档 (design document region 6, layout B)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

ASK = QColor("#e2534b")
BID = QColor("#3fb27f")


class OrderBookPanel(QWidget):
    HEADERS = ("档位", "价格", "量(手)")

    def __init__(self, parent=None):
        super().__init__(parent)
        title = QLabel("盘口五档")
        title.setStyleSheet("font-weight:600; padding:2px;")

        self.table = QTableWidget(10, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 42)
        self.table.setColumnWidth(2, 70)
        self.table.verticalHeader().setDefaultSectionSize(20)

        self.price = QLabel("—")
        self.price.setStyleSheet("font-size:18px; font-weight:700;")
        self.summary = QLabel("涨跌 —   均价 —   量 —")
        self.alerts = QLabel("预警：无")
        self.alerts.setWordWrap(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(title)
        lay.addWidget(self.table, 1)
        lay.addWidget(self.price)
        lay.addWidget(self.summary)
        lay.addWidget(self.alerts)

    def update_book(self, book) -> None:
        # 卖5..卖1 then 买1..买5
        rows = [("卖%d" % i, lv) for i, lv in zip(range(5, 0, -1), book.asks)] + \
               [("买%d" % i, lv) for i, lv in enumerate(book.bids, 1)]
        for r, (label, lv) in enumerate(rows):
            self._set(r, 0, label, ASK if label.startswith("卖") else BID)
            self._set(r, 1, f"{lv.price:.2f}" if lv.price else "—",
                      ASK if label.startswith("卖") else BID)
            self._set(r, 2, f"{lv.volume / 100:.0f}" if lv.volume else "—", None)
        self.price.setText(f"{book.price:.2f}" if book.price else "—")
        color = "#e2534b" if book.pct >= 0 else "#3fb27f"
        self.price.setStyleSheet(f"font-size:18px; font-weight:700; color:{color};")
        self.summary.setText(
            f"涨跌 {book.pct:+.2f}%   均价 {book.avg_price:.2f}   "
            f"量 {book.volume / 1e4:.1f}万")

    def set_alerts(self, lines: list[str]) -> None:
        self.alerts.setText("预警：" + ("；".join(lines) if lines else "无"))

    def _set(self, r: int, c: int, text: str, color: QColor | None) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if color is not None:
            item.setForeground(color)
        self.table.setItem(r, c, item)
