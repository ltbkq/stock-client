"""Render the running window to PNG for review.

    QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/screenshot.py

Writes /tmp/opencode/layout_a.png and /tmp/opencode/layout_b.png.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer                       # noqa: E402
from PySide6.QtWidgets import QApplication              # noqa: E402

from stockclient.alerts import AlertEngine              # noqa: E402
from stockclient.config import AppConfig                # noqa: E402
from stockclient.ui.main_window import MainWindow       # noqa: E402
from stockclient.workers import DataService             # noqa: E402

OUT = Path(os.environ.get("SHOT_OUT", tempfile.gettempdir()))


def main() -> int:
    cfg = AppConfig.load()
    cfg.demo_mode = True
    cfg.show_orderbook = False
    cfg.refresh_seconds = 1

    app = QApplication(sys.argv)
    win = MainWindow(cfg, DataService(cfg), AlertEngine())
    win.resize(1280, 800)
    win.show()
    win.start()

    steps = []

    def grab_a():
        win.grab().save(str(OUT / "layout_a.png"))
        win.book_btn.setChecked(True)          # switch to layout B
        QTimer.singleShot(1200, grab_b)

    def grab_b():
        win.grab().save(str(OUT / "layout_b.png"))
        app.quit()

    QTimer.singleShot(2200, grab_a)
    app.exec()
    for name in ("layout_a.png", "layout_b.png"):
        p = OUT / name
        print(name, p.stat().st_size if p.exists() else "MISSING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
