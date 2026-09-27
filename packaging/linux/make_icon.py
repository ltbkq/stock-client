"""Generate the 256x256 application icon (packaging/linux/stock-client.png).

    QT_QPA_PLATFORM=offscreen .venv/bin/python packaging/linux/make_icon.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui        # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

SIZE = 256
BG = "#161b22"
UP = "#e2534b"
DOWN = "#3fb27f"
LINE = "#f5c451"


def main() -> int:
    app = QApplication(sys.argv)
    pm = QtGui.QPixmap(SIZE, SIZE)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)

    p.setBrush(QtGui.QColor(BG))
    p.setPen(QtCore.Qt.NoPen)
    p.drawRoundedRect(0, 0, SIZE, SIZE, 44, 44)

    # candlesticks
    candles = [
        (40, 150, 96, True), (72, 120, 78, True), (104, 140, 110, False),
        (136, 96, 70, True), (168, 112, 58, True), (200, 74, 92, False),
    ]
    width = 20
    for x, top, height, rising in candles:
        color = QtGui.QColor(UP if rising else DOWN)
        p.setPen(QtGui.QPen(color, 3))
        p.drawLine(x + width // 2, top - 14, x + width // 2, top + height + 14)
        p.setBrush(color)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(x, top, width, height)

    # trend line
    p.setPen(QtGui.QPen(QtGui.QColor(LINE), 6, QtCore.Qt.SolidLine,
                        QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
    pts = [QtCore.QPointF(46, 176), QtCore.QPointF(88, 132),
           QtCore.QPointF(128, 150), QtCore.QPointF(176, 96), QtCore.QPointF(212, 118)]
    p.drawPolyline(QtGui.QPolygonF(pts))
    p.end()

    out = Path(__file__).with_name("stock-client.png")
    ok = pm.save(str(out))
    print("icon:", out, "->", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
