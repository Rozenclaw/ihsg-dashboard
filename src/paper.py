"""Paper-trading engine (Phase 3).

Simulates a virtual portfolio from the strategy's daily signals so you can
validate the approach before risking real money. Fully legal, no broker.

Logic per daily run (uses latest stored close as the fill price):
  - EXITS first: for each held position, sell if price >= target,
    price <= stop, or the signal turned SELL. (Frees cash before buys.)
  - ENTRIES: take BUY signals (best composite first) until cash/limits run out,
    sizing per strategy lots, respecting max positions.
Cash, positions, trades and a daily equity point are persisted to SQLite.

NOT financial advice. Simulated only.
"""
from __future__ import annotations

import pandas as pd

from . import db, strategy
from .config import get_config

LOT = strategy.LOT_SIZE
FEE_BPS = 15  # round-trip-ish brokerage proxy: 0.15% per side


def _cfg(cfg):
    p = {
        "starting_cash_idr": None,     # default -> strategy.portfolio_idr
        "max_positions": 10,
        "fee_bps": FEE_BPS,
    }
    p.update((cfg.get("paper") or {}))
    return p


def _price(symbol: str) -> float | None:
    df = db.load_prices(symbol)
    if df.empty:
        return None
    return float(df["close"].iloc[-1])


def _ensure_init(cfg) -> None:
    if db.get_state("initialized", 0.0) < 1.0:
        start = _cfg(cfg)["starting_cash_idr"] or strategy._strat(cfg)["portfolio_idr"]
        db.set_state("cash", float(start))
        db.set_state("start_equity", float(start))
        db.set_state("initialized", 1.0)


def _fee(value: float, cfg) -> float:
    return value * _cfg(cfg)["fee_bps"] / 10000.0


def run_day(cfg=None, run_date: str | None = None, recs=None) -> dict:
    """Advance the paper portfolio one day. Returns a summary dict."""
    cfg = cfg or get_config()
    db.init_db()
    _ensure_init(cfg)
    run_date = run_date or pd.Timestamp.today().strftime("%Y-%m-%d")
    pcfg = _cfg(cfg)

    if recs is None:
        recs = strategy.evaluate_universe(cfg)
    by_symbol = {r.symbol: r for r in recs}

    cash = db.get_state("cash")
    positions = {p["symbol"]: p for p in db.get_positions()}
    actions_log = []

    # ---- EXITS ----
    for sym, pos in list(positions.items()):
        px = _price(sym)
        if px is None:
            continue
        rec = by_symbol.get(sym)
        reason = None
        if pos["target"] and px >= pos["target"]:
            reason = "target hit"
        elif pos["stop"] and px <= pos["stop"]:
            reason = "stop hit"
        elif rec and rec.action == "SELL":
            reason = "signal SELL"
        if reason:
            value = pos["lots"] * LOT * px
            cash += value - _fee(value, cfg)
            db.add_trade(run_date, sym, "SELL", pos["lots"], px, value, reason)
            db.delete_position(sym)
            positions.pop(sym, None)
            actions_log.append(f"SELL {sym} ({reason})")

    # ---- ENTRIES ----
    buys = [r for r in recs if r.action == "BUY" and r.symbol not in positions]
    buys.sort(key=lambda r: -(r.composite or 0))
    for r in buys:
        if len(positions) >= pcfg["max_positions"]:
            break
        px = _price(r.symbol)
        if not px or not r.lots or r.lots <= 0:
            continue
        cost = r.lots * LOT * px
        fee = _fee(cost, cfg)
        if cost + fee > cash:
            # scale down to affordable lots
            affordable = int((cash / (1 + pcfg["fee_bps"] / 10000.0)) // (LOT * px))
            if affordable <= 0:
                continue
            r_lots = affordable
            cost = r_lots * LOT * px
            fee = _fee(cost, cfg)
        else:
            r_lots = r.lots
        cash -= cost + fee
        db.upsert_position(r.symbol, r_lots, px, run_date, r.target, r.stop)
        db.add_trade(run_date, r.symbol, "BUY", r_lots, px, cost, "signal BUY")
        positions[r.symbol] = {"symbol": r.symbol, "lots": r_lots, "avg_price": px,
                               "target": r.target, "stop": r.stop}
        actions_log.append(f"BUY {r.symbol} x{r_lots}")

    # ---- mark-to-market + persist ----
    holdings_val = 0.0
    for sym, pos in positions.items():
        px = _price(sym) or pos["avg_price"]
        holdings_val += pos["lots"] * LOT * px
    equity = cash + holdings_val
    db.set_state("cash", cash)
    db.record_equity(run_date, cash, holdings_val, equity)

    start_eq = db.get_state("start_equity", equity)
    return {
        "date": run_date, "cash": cash, "holdings": holdings_val, "equity": equity,
        "positions": len(positions), "actions": actions_log,
        "total_return_pct": (equity / start_eq - 1) * 100 if start_eq else 0.0,
    }


def portfolio_snapshot(cfg=None) -> dict:
    cfg = cfg or get_config()
    positions = db.get_positions()
    rows = []
    holdings_val = 0.0
    for pos in positions:
        px = _price(pos["symbol"]) or pos["avg_price"]
        mv = pos["lots"] * LOT * px
        cost = pos["lots"] * LOT * pos["avg_price"]
        holdings_val += mv
        rows.append({
            "Symbol": pos["symbol"], "Lots": pos["lots"], "Avg price": pos["avg_price"],
            "Last": px, "Market value": mv, "Unreal P/L": mv - cost,
            "Unreal P/L %": (px / pos["avg_price"] - 1) * 100 if pos["avg_price"] else 0.0,
            "Target": pos["target"], "Stop": pos["stop"],
        })
    cash = db.get_state("cash", 0.0)
    start_eq = db.get_state("start_equity", 0.0)
    equity = cash + holdings_val
    return {
        "rows": rows, "cash": cash, "holdings": holdings_val, "equity": equity,
        "start_equity": start_eq,
        "total_return_pct": (equity / start_eq - 1) * 100 if start_eq else 0.0,
    }


def reset(cfg=None) -> None:
    """Wipe paper state (fresh start)."""
    cfg = cfg or get_config()
    from .db import connect
    with connect() as conn:
        for t in ("paper_positions", "paper_trades", "paper_state", "paper_equity"):
            conn.execute(f"DELETE FROM {t}")
    _ensure_init(cfg)
