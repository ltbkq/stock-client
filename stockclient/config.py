"""User configuration persisted as JSON (no Qt dependency)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .sample import WATCHLIST

CONFIG_DIR = Path.home() / ".config" / "stock-client"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    groups: dict[str, list[tuple[str, str]]] = field(
        default_factory=lambda: {"默认": list(WATCHLIST)})
    period: str = "day"
    adjust: str = "pre"
    theme: str = "dark"                # dark | light
    refresh_seconds: int = 5
    show_orderbook: bool = False       # 布局 A(False) / B(True)
    data_source: str = "eastmoney"
    demo_mode: bool = False

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "AppConfig":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        cfg = cls()
        for key, value in raw.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg

    def save(self, path: Path = CONFIG_PATH) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                              encoding="utf-8")
