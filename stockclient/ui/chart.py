"""K-line chart: candlesticks + overlay (MA/BOLL) + volume + switchable indicator.

Built on pyqtgraph so wheel-zoom / drag-pan come for free; the three plots share
one X axis (a time axis) exactly like the design document's main/volume/indicator
stack.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from .. import indicators as ind
from ..models import Bar

UP = "#e2534b"
DOWN = "#3fb27f"
GRID = (120, 120, 120, 60)


class CandlestickItem(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self._picture = QtGui.QPicture()
        self._bounds = QtCore.QRectF()
        self._width = 1.0

    def set_bars(self, bars: list[Bar]) -> None:
        self._generate(bars)
        self.informViewBoundsChanged()
        self.update()

    def _generate(self, bars: list[Bar]) -> None:
        self._picture = QtGui.QPicture()
        self._bounds = QtCore.QRectF()
        if not bars:
            return
        xs = np.array([b.dt.timestamp() for b in bars])
        span = float(np.median(np.diff(xs))) if len(xs) > 1 else 60.0
        self._width = span * 0.6
        half = self._width / 2

        painter = QtGui.QPainter(self._picture)
        lows = np.array([b.low for b in bars])
        highs = np.array([b.high for b in bars])
        ymin, ymax = lows.min(), highs.max()
        for x, bar in zip(xs, bars):
            rising = bar.close >= bar.open
            color = UP if rising else DOWN
            pen = QtGui.QPen(QtGui.QColor(color))
            pen.setCosmetic(True)          # pen width is device px, not data units
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.drawLine(QtCore.QPointF(x, bar.low), QtCore.QPointF(x, bar.high))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(color)))
            top = max(bar.open, bar.close)
            height = abs(bar.close - bar.open)
            painter.drawRect(QtCore.QRectF(x - half, top, self._width, max(height, 1e-6)))
        painter.end()
        pad = (ymax - ymin) * 0.05 or 1.0
        self._bounds = QtCore.QRectF(xs[0] - span, ymin - pad, xs[-1] - xs[0] + 2 * span,
                                     (ymax - ymin) + 2 * pad)

    def paint(self, painter, *args) -> None:        # noqa: D102
        self._picture.play(painter)

    def boundingRect(self) -> QtCore.QRectF:        # noqa: D102
        return self._bounds


class KLineChart(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        pg.setConfigOptions(antialias=True, background="#1b1e24", foreground="#c8ccd4")

        self.glw = pg.GraphicsLayoutWidget()
        self.main = self.glw.addPlot(row=0, col=0)
        self.vol = self.glw.addPlot(row=1, col=0)
        self.ind = self.glw.addPlot(row=2, col=0)
        self.glw.ci.layout.setRowStretchFactor(0, 6)
        self.glw.ci.layout.setRowStretchFactor(1, 2)
        self.glw.ci.layout.setRowStretchFactor(2, 2)

        self.axis = pg.DateAxisItem(orientation="bottom")
        self.ind.setAxisItems({"bottom": self.axis})
        for p in (self.main, self.vol):
            p.getAxis("bottom").setStyle(showValues=False)
        self.vol.setXLink(self.main)
        self.ind.setXLink(self.main)
        for p in (self.main, self.vol, self.ind):
            p.showGrid(x=True, y=True, alpha=0.15)
            p.getAxis("right").setStyle(showValues=False)
            p.getAxis("left").setTextPen("#c8ccd4")

        self.candles = CandlestickItem()
        self.main.addItem(self.candles)
        self.vol.setLabel("left", "成交量")
        self.ind.setLabel("left", "MACD")

        # crosshair + readout
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#7f8592", style=QtCore.Qt.DashLine))
        self.hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#7f8592", style=QtCore.Qt.DashLine))
        self.main.addItem(self.vline, ignoreBounds=True)
        self.main.addItem(self.hline, ignoreBounds=True)
        self.legend = pg.TextItem(color="#d8dbe2", anchor=(0, 1))
        self.main.addItem(self.legend, ignoreBounds=True)
        self.main.scene().sigMouseMoved.connect(self._on_mouse)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.glw)

        self._bars: list[Bar] = []
        self._intraday = False
        self._overlay = "MA"
        self._indicator = "MACD"

    # -- public API --------------------------------------------------------
    def set_bars(self, bars: list[Bar], intraday: bool = False) -> None:
        if intraday:
            self.set_intraday(bars)
            return
        self._intraday = False
        self._bars = bars or []
        self.candles.setVisible(True)
        self.candles.set_bars(self._bars)
        self._draw_overlay()
        self._draw_volume()
        self._draw_indicator()
        if self._bars:
            xs = [b.dt.timestamp() for b in self._bars]
            self.main.setXRange(xs[0], xs[-1], padding=0.02)
            self.main.enableAutoRange(axis="y", enable=True)

    def set_intraday(self, bars: list[Bar]) -> None:
        """分时图：主图走势线 + 均价线，副图分钟成交量（不复用蜡烛渲染）。"""
        self._intraday = True
        self._bars = bars or []
        self.candles.set_bars([])          # 清空蜡烛，主图改画分时线
        self.candles.setVisible(False)     # 隐藏以免空包围盒把 Y 轴拉到 0
        self._clear_dynamic()
        if not self._bars:
            self.vol.clear()
            self.ind.clear()
            return
        xs = np.array([b.dt.timestamp() for b in self._bars])
        close = ind.close_array(self._bars)
        avg = ind.avg_price(self._bars)
        gx, gclose = ind.break_gaps(xs, close)
        _, gavg = ind.break_gaps(xs, avg)
        self._dyn.append(self.main.plot(gx, gclose, pen=pg.mkPen("#d8dbe2", width=1.4)))
        self._dyn.append(self.main.plot(gx, gavg, pen=pg.mkPen("#f5c451", width=1.2)))
        self._draw_volume()
        self._draw_indicator()
        self.main.setXRange(xs[0], xs[-1], padding=0.02)
        self.main.enableAutoRange(axis="y", enable=True)

    def set_overlay(self, kind: str) -> None:
        self._overlay = kind
        self._draw_overlay()

    def set_indicator(self, kind: str) -> None:
        self._indicator = kind
        self.ind.setLabel("left", kind)
        self._draw_indicator()

    # -- drawing helpers ---------------------------------------------------
    def _clear_dynamic(self) -> None:
        for item in getattr(self, "_dyn", []):
            try:
                self.main.removeItem(item)
            except Exception:
                pass
        self._dyn = []

    def _draw_overlay(self) -> None:
        if self._intraday:
            return                       # 分时只用走势线 + 均价线，不用 MA/BOLL 叠加
        self._clear_dynamic()
        if not self._bars:
            return
        xs = np.array([b.dt.timestamp() for b in self._bars])
        close = ind.close_array(self._bars)
        if self._overlay == "MA":
            for n, color in ((5, "#f5c451"), (10, "#4aa3ff"), (20, "#c77dff"), (60, "#8bd450")):
                y = ind.ma(close, n)
                self._dyn.append(self.main.plot(xs, y, pen=pg.mkPen(color, width=1.1), name=f"MA{n}"))
        elif self._overlay == "BOLL":
            up, mid, low = ind.boll(close, 20, 2.0)
            self._dyn.append(self.main.plot(xs, up, pen=pg.mkPen("#4aa3ff", width=1.0)))
            self._dyn.append(self.main.plot(xs, mid, pen=pg.mkPen("#f5c451", width=1.0)))
            self._dyn.append(self.main.plot(xs, low, pen=pg.mkPen("#4aa3ff", width=1.0)))

    def _draw_volume(self) -> None:
        self.vol.clear()
        if not self._bars:
            return
        xs = np.array([b.dt.timestamp() for b in self._bars])
        vols = np.array([b.volume for b in self._bars])
        span = float(np.median(np.diff(xs))) if len(xs) > 1 else 60.0
        if self._intraday:
            # 分钟量按相对前一根涨跌着色
            colors = []
            prev = self._bars[0].open
            for b in self._bars:
                colors.append((226, 83, 75, 180) if b.close >= prev else (63, 178, 127, 180))
                prev = b.close
        else:
            colors = [(226, 83, 75, 180) if b.close >= b.open else (63, 178, 127, 180)
                      for b in self._bars]
        self._vol_bars = pg.BarGraphItem(x=xs, height=vols, width=span * 0.6, brushes=colors)
        self.vol.addItem(self._vol_bars)
        for n, color in ((5, "#f5c451"), (10, "#4aa3ff")):
            y = ind.ma(vols, n)
            gx, gy = ind.break_gaps(xs, y) if self._intraday else (xs, y)
            self.vol.plot(gx, gy, pen=pg.mkPen(color, width=1.0))

    def _draw_indicator(self) -> None:
        self.ind.clear()
        if not self._bars:
            return
        xs = np.array([b.dt.timestamp() for b in self._bars])
        close = ind.close_array(self._bars)
        high = np.array([b.high for b in self._bars])
        low = np.array([b.low for b in self._bars])
        span = float(np.median(np.diff(xs))) if len(xs) > 1 else 60.0

        def line(y, pen):
            gx, gy = ind.break_gaps(xs, y) if self._intraday else (xs, y)
            self.ind.plot(gx, gy, pen=pen)

        if self._indicator == "MACD":
            dif, dea, hist = ind.macd(close)
            colors = [(226, 83, 75, 180) if v >= 0 else (63, 178, 127, 180) for v in np.nan_to_num(hist)]
            self.ind.addItem(pg.BarGraphItem(x=xs, height=hist, width=span * 0.6, brushes=colors))
            line(dif, pg.mkPen("#f5c451", width=1.1))
            line(dea, pg.mkPen("#4aa3ff", width=1.1))
        elif self._indicator == "KDJ":
            k, d, j = ind.kdj(high, low, close)
            line(k, pg.mkPen("#f5c451"))
            line(d, pg.mkPen("#4aa3ff"))
            line(j, pg.mkPen("#c77dff"))
        elif self._indicator == "RSI":
            line(ind.rsi(close, 14), pg.mkPen("#f5c451"))

    def _on_mouse(self, pos) -> None:
        if not self._bars or not self.main.sceneBoundingRect().contains(pos):
            return
        point = self.main.vb.mapSceneToView(pos)
        self.vline.setPos(point.x())
        self.hline.setPos(point.y())
        idx = int(np.argmin([abs(b.dt.timestamp() - point.x()) for b in self._bars]))
        b = self._bars[idx]
        self.legend.setText(
            f"{b.dt:%Y-%m-%d %H:%M}  开{b.open:g} 高{b.high:g} 低{b.low:g} 收{b.close:g}  "
            f"量{b.volume/1e4:.1f}万")
        self.legend.setPos(point.x(), self.main.vb.viewRange()[1][1])
