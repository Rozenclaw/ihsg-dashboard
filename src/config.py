"""Configuration loader. Reads config.yaml from the project root."""
from __future__ import annotations

import os
from functools import lru_cache

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")

DEFAULTS = {
    "database": {"path": "data/ihsg.db"},
    "data": {
        "source": "yfinance",
        "index_symbol": "^JKSE",
        "history_period": "2y",
        "history_interval": "1d",
        "request_pause_sec": 1.0,
    },
    "indicators": {
        "sma_fast": 50,
        "sma_slow": 200,
        "rsi_period": 14,
        "bb_period": 20,
        "bb_std": 2.0,
    },
    "dashboard": {"default_watchlist": ["BBRI.JK", "PTBA.JK", "TLKM.JK"]},
    "stacking": {
        "monthly_budget_idr": 5_000_000,
        "num_stocks": 3,
        "use_entry_price": True,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@lru_cache(maxsize=1)
def get_config() -> dict:
    cfg = DEFAULTS
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh) or {}
        cfg = _deep_merge(DEFAULTS, loaded)
    return cfg


def db_path() -> str:
    p = get_config()["database"]["path"]
    if not os.path.isabs(p):
        p = os.path.join(PROJECT_ROOT, p)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p
