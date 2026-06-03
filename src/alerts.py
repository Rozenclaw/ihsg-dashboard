"""Per-stock price / RSI alerts (Tier 1).

Define alerts like "BBRI price below 4000" or "PTBA RSI below 35". The daily job
(or the dashboard) checks them against the latest stored data and fires a
notification when the condition is met. Fired alerts are de-duplicated per day
so you don't get spammed.

NOT financial advice.
"""
from __future__ import annotations

import pandas as pd

from . import db, indicators
from .config import get_config

METRICS = ("price", "rsi")
OPS = ("below", "above")


def _current(symbol: str, metric: str, cfg: dict):
    df = indicators.enrich(db.load_prices(symbol), cfg)
    if df.empty:
        return None
    snap = indicators.snapshot(df, cfg)
    return snap.get("close") if metric == "price" else snap.get("rsi")


def _triggered(value: float, op: str, threshold: float) -> bool:
    if value is None:
        return False
    return value <= threshold if op == "below" else value >= threshold


def check_alerts(cfg=None, fire: bool = True) -> list[dict]:
    """Evaluate all active alerts. Returns a list of triggered alert dicts.

    Each triggered alert is marked fired for today (so repeated runs the same
    day won't re-notify). If `fire` is False, nothing is persisted (dry run).
    """
    cfg = cfg or get_config()
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    out = []
    for a in db.list_alerts(active_only=True):
        if a.get("last_fired") == today:
            continue  # already notified today
        val = _current(a["symbol"], a["metric"], cfg)
        if _triggered(val, a["op"], a["threshold"]):
            a["current_value"] = val
            out.append(a)
            if fire:
                db.mark_alert_fired(a["id"], today)
    return out


def format_alert(a: dict) -> str:
    unit = "" if a["metric"] == "rsi" else ""
    val = a.get("current_value")
    valstr = f"{val:,.0f}" if (val is not None and a["metric"] == "price") \
        else (f"{val:.0f}" if val is not None else "—")
    base = (f"🔔 {a['symbol']}: {a['metric'].upper()} {a['op']} "
            f"{a['threshold']:,.0f} (now {valstr})")
    return base + (f" — {a['note']}" if a.get("note") else "")


def format_digest(triggered: list[dict]) -> str:
    if not triggered:
        return ""
    return "🔔 Alerts triggered:\n" + "\n".join("  " + format_alert(a) for a in triggered)
