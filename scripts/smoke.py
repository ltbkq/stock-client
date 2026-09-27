"""Headless smoke test: build the full window in demo mode, run the poller for
a moment and assert that watchlist / chart / order book all received data.

    QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/smoke.py
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


def main() -> int:
    cfg = AppConfig.load()
    cfg.demo_mode = True
    cfg.show_orderbook = True
    cfg.refresh_seconds = 1

    app = QApplication(sys.argv)
    win = MainWindow(cfg, DataService(cfg), AlertEngine())
    win.show()
    win.start()

    result = {}

    def check() -> None:
        result["symbol"] = win.current
        result["bars"] = len(win.chart._bars)
        result["row_pct"] = win.watchlist.table.item(0, 2).text()
        result["book_price"] = win.orderbook.price.text()
        result["status"] = win.lbl_time.text()
        out = Path(os.environ.get("SMOKE_OUT", tempfile.gettempdir())) / "stockclient_smoke.png"
        saved = win.chart.grab().save(str(out))
        result["png"] = bool(saved) and out.exists() and out.stat().st_size
        app.quit()

    QTimer.singleShot(2500, check)
    app.exec()

    print("symbol      :", result["symbol"])
    print("bars        :", result["bars"])
    print("watchlist % :", result["row_pct"])
    print("book price  :", result["book_price"])
    print("status      :", result["status"])
    print("png bytes   :", result["png"])

    ok = result["bars"] > 0 and result["row_pct"].startswith(("+", "-")) \
        and result["book_price"] not in ("", "—") and result["png"]
    print("SMOKE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
