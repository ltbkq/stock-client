"""Data-source configuration loader.

Endpoint URLs, request parameters, field mappings and rate limits all live in
``data_sources.json`` so an interface change never requires touching Python.

Two layers are merged (user wins, field by field):

1. packaged default  ``stockclient/data_sources.json``  (ships with the app)
2. user override     ``~/.config/stock-client/data_sources.json``

Call :func:`export_user_config` to write the effective config to the user path
for editing.  See README「数据源配置」.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).with_name("data_sources.json")
USER_PATH = Path(os.environ.get("STOCKCLIENT_CONFIG_DIR", Path.home() / ".config" / "stock-client")) \
    / "data_sources.json"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into ``base`` (returns a new dict)."""
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_data_sources(path: str | Path | None = None) -> dict[str, Any]:
    """Load the packaged defaults merged with the user override."""
    with open(DEFAULT_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    user = Path(path) if path else USER_PATH
    if user and Path(user).is_file():
        with open(user, encoding="utf-8") as fh:
            data = _deep_merge(data, json.load(fh))
    return data


def load_source(name: str | None = None) -> dict[str, Any]:
    """Return one source block (defaults to ``active``)."""
    data = load_data_sources()
    sources = data.get("sources") or {}
    key = name or data.get("active") or next(iter(sources), "")
    if key not in sources:
        raise KeyError(f"unknown data source {key!r}; available: {list(sources)}")
    source = copy.deepcopy(sources[key])
    source.setdefault("name", key)
    return source


def export_user_config(path: str | Path | None = None) -> Path:
    """Write the effective config to the user override path for editing."""
    target = Path(path) if path else USER_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_effective_defaults(), ensure_ascii=False, indent=2),
        encoding="utf-8")
    return target


def _effective_defaults() -> dict[str, Any]:
    with open(DEFAULT_PATH, encoding="utf-8") as fh:
        return json.load(fh)
