"""Entry point.

    python run.py --demo        # offline, deterministic sample data
    python run.py               # live East Money data
    python run.py --no-proxy    # live, bypass a misbehaving system proxy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from stockclient.alerts import AlertEngine
from stockclient.cache import BarCache
from stockclient.config import AppConfig
from stockclient.eastmoney import EastMoneyClient
from stockclient.ui.main_window import MainWindow
from stockclient.workers import DataService


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="自选股行情分析客户端")
    ap.add_argument("--demo", action="store_true", help="使用内置离线数据")
    ap.add_argument("--no-proxy", action="store_true", help="忽略系统代理直连")
    args = ap.parse_args(argv)

    cfg = AppConfig.load()
    if args.demo:
        cfg.demo_mode = True

    client = None
    cache = None
    if not cfg.demo_mode:
        client = EastMoneyClient(trust_env=not args.no_proxy)
        cache_dir = Path.home() / ".cache" / "stock-client"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = BarCache(cache_dir / "bars.db")

    service = DataService(cfg, client=client, cache=cache)

    app = QApplication(sys.argv)
    app.setApplicationName("stock-client")
    app.setApplicationDisplayName("自选股行情分析客户端")

    win = MainWindow(cfg, service, AlertEngine())
    win.show()
    win.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
