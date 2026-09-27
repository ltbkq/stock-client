"""Main window: assembles the layout from the design document (regions 1-9)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDockWidget, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QStatusBar, QSystemTrayIcon,
    QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from ..alerts import AlertEngine
from ..config import AppConfig
from ..eastmoney import SOURCE_LABEL
from ..workers import DataService, PollController
from . import style
from .alerts_dialog import AlertsDialog
from .chart import KLineChart
from .orderbook import OrderBookPanel
from .watchlist import WatchlistPanel

PERIODS = [("分时", "intraday"), ("1分", "1m"), ("5分", "5m"), ("15分", "15m"),
           ("30分", "30m"), ("60分", "60m"), ("日线", "day"), ("周线", "week"),
           ("月线", "month")]
ADJUSTS = [("前复权", "pre"), ("不复权", "none"), ("后复权", "post")]


class MainWindow(QMainWindow):
    def __init__(self, cfg: AppConfig, service: DataService, engine: AlertEngine):
        super().__init__()
        self.cfg = cfg
        self.service = service
        self.engine = engine
        self.current = ("", "")

        self.setWindowTitle("自选股行情分析客户端")
        self.resize(1280, 800)
        self.setStyleSheet(style.sheet(cfg.theme))

        self.chart = KLineChart()
        self.watchlist = WatchlistPanel(cfg.groups)
        self.orderbook = OrderBookPanel()

        self._build_toolbar()
        self._build_docks()
        self._build_bottom_bar()
        self._build_status_bar()
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self.chart, 1)
        lay.addWidget(self._bottom)
        self.setCentralWidget(central)

        self.controller = PollController(service, engine)
        self.controller.quoteReady.connect(self._on_quote)
        self.controller.bookReady.connect(self._on_book)
        self.controller.barsReady.connect(self._on_bars)
        self.controller.triggered.connect(self._on_alert)
        self.controller.failed.connect(self._on_failed)
        self.watchlist.symbolSelected.connect(self._select)

        self._tray = QSystemTrayIcon(self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon), self)
        self._tray.show()

        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Space"), self, self.controller.refresh_now)
        QShortcut(QKeySequence("Ctrl+E"), self, self._export)

        # first symbol
        first = next(iter(cfg.groups.values()), [])
        if first:
            self.watchlist.table.selectRow(0)

    # -- construction ------------------------------------------------------
    def _build_toolbar(self) -> None:
        bar = QToolBar("主工具栏")
        bar.setMovable(False)
        self.addToolBar(bar)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索：代码 / 名称")
        self.search.setFixedWidth(180)
        self.search.returnPressed.connect(self._search)
        bar.addWidget(self.search)

        self.period = QComboBox()
        self.period.addItems([p[0] for p in PERIODS])
        self.period.setCurrentIndex(max(0, [p[1] for p in PERIODS].index(self.cfg.period)))
        self.period.currentIndexChanged.connect(
            lambda i: self.controller.set_period(PERIODS[i][1]))
        bar.addWidget(QLabel(" 周期 "))
        bar.addWidget(self.period)

        self.adjust = QComboBox()
        self.adjust.addItems([a[0] for a in ADJUSTS])
        self.adjust.setCurrentIndex(max(0, [a[1] for a in ADJUSTS].index(self.cfg.adjust)))
        self.adjust.currentIndexChanged.connect(
            lambda i: self.controller.set_adjust(ADJUSTS[i][1]))
        bar.addWidget(QLabel(" 复权 "))
        bar.addWidget(self.adjust)

        self.book_btn = QToolButton()
        self.book_btn.setText("五档")
        self.book_btn.setCheckable(True)
        self.book_btn.setChecked(self.cfg.show_orderbook)
        self.book_btn.toggled.connect(self._toggle_book)
        bar.addWidget(self.book_btn)

        alert_btn = QToolButton()
        alert_btn.setText("预警")
        alert_btn.clicked.connect(self._add_alert)
        bar.addWidget(alert_btn)

        refresh = QToolButton()
        refresh.setText("刷新")
        refresh.clicked.connect(lambda: self.controller.refresh_now())
        bar.addWidget(refresh)

        theme = QToolButton()
        theme.setText("主题")
        theme.clicked.connect(self._toggle_theme)
        bar.addWidget(theme)

    def _build_docks(self) -> None:
        left = QDockWidget("自选股", self)
        left.setWidget(self.watchlist)
        left.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.LeftDockWidgetArea, left)

        self.book_dock = QDockWidget("盘口五档", self)
        self.book_dock.setWidget(self.orderbook)
        self.book_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.book_dock)
        self.book_dock.setVisible(self.cfg.show_orderbook)

    def _build_bottom_bar(self) -> None:
        self._bottom = QWidget()
        row = QHBoxLayout(self._bottom)
        row.setContentsMargins(6, 2, 6, 2)
        for label, period in (("分时", "intraday"), ("日K", "day"),
                              ("周K", "week"), ("月K", "month")):
            btn = QPushButton(label)
            btn.setFixedWidth(52)
            btn.clicked.connect(lambda _=False, p=period: self._quick_period(p))
            row.addWidget(btn)

        row.addWidget(QLabel("  指标 "))
        self.indicator = QComboBox()
        self.indicator.addItems(["MACD", "KDJ", "RSI"])
        self.indicator.currentTextChanged.connect(self.chart.set_indicator)
        row.addWidget(self.indicator)

        row.addWidget(QLabel(" 叠加 "))
        self.overlay = QComboBox()
        self.overlay.addItems(["MA", "BOLL"])
        self.overlay.currentTextChanged.connect(self.chart.set_overlay)
        row.addWidget(self.overlay)

        row.addStretch(1)
        export = QPushButton("导出")
        export.clicked.connect(self._export)
        full = QPushButton("全屏")
        full.clicked.connect(self._toggle_fullscreen)
        row.addWidget(export)
        row.addWidget(full)

    def _build_status_bar(self) -> None:
        self.sb = QStatusBar()
        self.setStatusBar(self.sb)
        label = "演示(离线)" if self.service.offline else SOURCE_LABEL
        self.lbl_source = QLabel(f"数据源: {label}")
        self.lbl_time = QLabel("最后更新: —")
        self.lbl_conn = QLabel("[已连接]")
        self.lbl_alert = QLabel("预警: 0")
        for w in (self.lbl_source, self.lbl_time, self.lbl_conn, self.lbl_alert):
            self.sb.addPermanentWidget(w)

    # -- slots -------------------------------------------------------------
    def _select(self, code: str, name: str) -> None:
        self.current = (code, name)
        self.setWindowTitle(f"{name} {code} - 自选股行情分析客户端")
        self.controller.set_symbol(code)
        self.controller.set_orderbook(self.book_dock.isVisible())

    def _on_quote(self, quote) -> None:
        self.watchlist.update_quote(quote)
        self.lbl_time.setText(f"最后更新: {quote.ts:%Y-%m-%d %H:%M:%S}" if quote.ts else "最后更新: —")
        if self.lbl_conn.text() != "[已连接]":
            self.lbl_conn.setText("[已连接]")
            self.lbl_conn.setStyleSheet("color:#3fb27f;")

    def _on_book(self, book) -> None:
        self.orderbook.update_book(book)

    def _on_bars(self, code: str, bars) -> None:
        if code == self.current[0]:
            self.chart.set_bars(bars, intraday=(self.controller.period == "intraday"))

    def _on_alert(self, trigger) -> None:
        self._triggered = getattr(self, "_triggered", [])
        self._triggered.append(trigger.message)
        self.lbl_alert.setText(f"预警: {len(self._triggered)}")
        self.orderbook.set_alerts(self._triggered[-4:])
        if QSystemTrayIcon.supportsMessages():
            self._tray.showMessage("价格预警", trigger.message, QSystemTrayIcon.Warning, 6000)

    def _on_failed(self, message: str) -> None:
        self.lbl_conn.setText("[离线] 展示缓存数据")
        self.lbl_conn.setStyleSheet("color:#e2534b;")
        self.statusBar().showMessage(message[:80], 4000)

    # -- actions -----------------------------------------------------------
    def _search(self) -> None:
        code = self.search.text().strip()
        if code:
            self._select(code, code)

    def _quick_period(self, period: str) -> None:
        idx = [p[1] for p in PERIODS].index(period)
        self.period.setCurrentIndex(idx)

    def _toggle_book(self, on: bool) -> None:
        self.book_dock.setVisible(on)
        self.controller.set_orderbook(on)

    def _toggle_theme(self) -> None:
        self.cfg.theme = "light" if self.cfg.theme == "dark" else "dark"
        self.setStyleSheet(style.sheet(self.cfg.theme))

    def _toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出图表", "chart.png", "PNG (*.png)")
        if path:
            self.chart.grab().save(path)

    def _add_alert(self) -> None:
        if not self.current[0]:
            return
        AlertsDialog(self.engine, self.current, parent=self).exec()

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        self.controller.start()

    def closeEvent(self, event) -> None:        # noqa: N802
        self.controller.stop()
        self.cfg.show_orderbook = self.book_dock.isVisible()
        self.cfg.period = PERIODS[self.period.currentIndex()][1]
        self.cfg.adjust = ADJUSTS[self.adjust.currentIndex()][1]
        self.cfg.save()
        self.service.cache and self.service.cache.close()
        super().closeEvent(event)
