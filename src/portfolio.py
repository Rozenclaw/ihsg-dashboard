"""Real holdings tracking (Tier 2).

Import your actual broker positions (CSV: symbol, lots, avg_price) and the
dashboard tracks YOUR live P/L from stored prices, plus flags when any of your
holdings flips to a SELL signal in the strategy.

Pure local — nothing leaves your machine. NOT financial advice.
"""
from __future__ import annotations

import csv
import io

import pandas as pd

from . import db, strategy
from .config import get_config

LOT = strategy.LOT_SIZE


def parse_csv(text: str) -> tuple[list[dict], list[str]]:
    """Parse pasted CSV into holding rows. Returns (rows, errors).

    Expected header: symbol,lots,avg_price[,note]. Symbol gets .JK appended.
    """
    rows, errors = [], []
    if not text or not text.strip():
        return rows, ["empty input"]
    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames:
        return rows, ["no header row found"]
    norm = {f.lower().strip(): f for f in reader.fieldnames}
    if "symbol" not in norm or "lots" not in norm or "avg_price" not in norm:
        return rows, ["header must include: symbol, lots, avg_price"]
    for i, r in enumerate(reader, 2):
        try:
            sym = (r[norm["symbol"]] or "").strip().upper()
            if not sym:
                continue
            if not sym.endswith(".JK"):
                sym += ".JK"
            lots = int(float(r[norm["lots"]]))
            avg = float(r[norm["avg_price"]])
            note = r.get(norm.get("note", ""), "") if "note" in norm else ""
            rows.append({"symbol": sym, "lots": lots, "avg_price": avg, "note": note})
        except (ValueError, KeyError, TypeError) as e:
            errors.append(f"row {i}: {e}")
    return rows, errors


def import_csv(text: str, replace: bool = True) -> tuple[int, list[str]]:
    rows, errors = parse_csv(text)
    if replace and rows:
        db.clear_holdings()
    for r in rows:
        db.set_holding(r["symbol"], r["lots"], r["avg_price"], r.get("note", ""))
    return len(rows), errors


def _last_price(symbol: str) -> float | None:
    dfp = db.load_prices(symbol)
    return float(dfp["close"].iloc[-1]) if not dfp.empty else None


def snapshot(cfg=None) -> dict:
    """Live P/L for your real holdings, plus the current signal per holding."""
    cfg = cfg or get_config()
    holds = db.list_holdings()
    if not holds:
        return {"rows": [], "cost": 0.0, "value": 0.0, "pl": 0.0, "pl_pct": 0.0,
                "sell_flags": []}
    # current signals (cached upstream) for action lookup
    sig = {r.symbol: r for r in strategy.evaluate_universe(cfg)} if holds else {}
    rows, total_cost, total_val, sell_flags = [], 0.0, 0.0, []
    for h in holds:
        px = _last_price(h["symbol"]) or h["avg_price"]
        cost = h["lots"] * LOT * h["avg_price"]
        val = h["lots"] * LOT * px
        total_cost += cost
        total_val += val
        rec = sig.get(h["symbol"])
        action = rec.action if rec else "—"
        if action == "SELL":
            sell_flags.append(h["symbol"])
        rows.append({
            "Symbol": h["symbol"], "Lots": h["lots"], "Avg price": h["avg_price"],
            "Last": px, "Cost": cost, "Value": val, "P/L": val - cost,
            "P/L %": (px / h["avg_price"] - 1) * 100 if h["avg_price"] else 0.0,
            "Signal": action, "Note": h.get("note") or "",
        })
    return {
        "rows": rows, "cost": total_cost, "value": total_val,
        "pl": total_val - total_cost,
        "pl_pct": (total_val / total_cost - 1) * 100 if total_cost else 0.0,
        "sell_flags": sell_flags,
    }
