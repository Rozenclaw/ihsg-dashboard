"""Backtest engine (Phase 3).

Walks historical daily bars, re-computing the dividend+value strategy on a
point-in-time slice of price history each step (no lookahead), simulating a
simple long-only portfolio, and comparing results to buy-and-hold IHSG.

Fundamentals (dividend/beta) aren't point-in-time on the free tier, so the
backtest uses the *current* fundamentals as a static proxy and focuses on the
technical timing component. Treat results as indicative, not precise.

NOT financial advice.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import db, indicators, strategy
from .config import get_config

LOT = strategy.LOT_SIZE


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    return float(dd.min() * 100)


def _cagr(equity: pd.Series, periods_per_year: int = 252) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = len(equity) / periods_per_year
    if years <= 0:
        return 0.0
    return float(((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) * 100)


def _sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    if returns.std() == 0 or returns.empty:
        return 0.0
    return float(np.sqrt(periods_per_year) * returns.mean() / returns.std())


def run(cfg=None, lookback_days: int = 504, rebalance_every: int = 5,
        max_positions: int = 10, symbols: list[str] | None = None) -> dict:
    """Run a simple walk-forward backtest. Returns metrics + equity curve."""
    cfg = cfg or get_config()
    strat = strategy._strat(cfg)
    start_cash = strat["portfolio_idr"]
    idx_sym = cfg["data"]["index_symbol"]

    if symbols is None:
        symbols = db.list_symbols(include_index=False)

    # Preload enriched price frames once.
    frames = {}
    for s in symbols:
        df = indicators.enrich(db.load_prices(s), cfg)
        if not df.empty and len(df) >= strat["min_history_days"] + 5:
            frames[s] = df
    if not frames:
        return {"error": "not enough history to backtest"}

    # Common trading calendar = union of dates, tail lookback.
    all_dates = sorted(set().union(*[set(df.index) for df in frames.values()]))
    all_dates = all_dates[-lookback_days:]
    if len(all_dates) < 30:
        return {"error": "insufficient overlapping history"}

    cash = float(start_cash)
    positions: dict[str, dict] = {}  # symbol -> {lots, avg, target, stop}
    equity_points = []

    fundamentals = {s: db.load_fundamentals(s) for s in frames}

    for i, dt in enumerate(all_dates):
        # current prices as of dt
        prices = {}
        for s, df in frames.items():
            sub = df.loc[:dt]
            if not sub.empty and sub.index[-1] == dt:
                prices[s] = float(sub["close"].iloc[-1])

        # exits (check every day)
        for s, pos in list(positions.items()):
            px = prices.get(s)
            if px is None:
                continue
            if (pos["target"] and px >= pos["target"]) or (pos["stop"] and px <= pos["stop"]):
                cash += pos["lots"] * LOT * px
                positions.pop(s)

        # rebalance / entries every N days
        if i % rebalance_every == 0:
            ranked = []
            for s, df in frames.items():
                sub = df.loc[:dt]
                if len(sub) < strat["min_history_days"]:
                    continue
                rec = strategy.evaluate(s, cfg, df_enriched=sub, fund=fundamentals.get(s))
                if rec.action == "BUY" and s not in positions and rec.lots:
                    ranked.append((rec.composite or 0, rec))
            ranked.sort(key=lambda x: -x[0])
            for _, rec in ranked:
                if len(positions) >= max_positions:
                    break
                px = prices.get(rec.symbol)
                if not px:
                    continue
                cost = rec.lots * LOT * px
                if cost > cash:
                    affordable = int(cash // (LOT * px))
                    if affordable <= 0:
                        continue
                    lots = affordable
                    cost = lots * LOT * px
                else:
                    lots = rec.lots
                cash -= cost
                positions[rec.symbol] = {"lots": lots, "avg": px,
                                         "target": rec.target, "stop": rec.stop}

        # mark to market
        mv = sum(pos["lots"] * LOT * prices.get(s, pos["avg"])
                 for s, pos in positions.items())
        equity_points.append((dt, cash + mv))

    eq = pd.Series({d: v for d, v in equity_points}).sort_index()
    rets = eq.pct_change().dropna()

    # Benchmark: buy & hold IHSG over same window.
    bench = db.load_prices(idx_sym)
    bench_ret = None
    if not bench.empty:
        b = bench["close"].reindex(eq.index, method="ffill").dropna()
        if len(b) > 1 and b.iloc[0] > 0:
            bench_ret = (b.iloc[-1] / b.iloc[0] - 1) * 100

    return {
        "equity": eq,
        "start_equity": float(eq.iloc[0]) if len(eq) else start_cash,
        "end_equity": float(eq.iloc[-1]) if len(eq) else start_cash,
        "total_return_pct": float((eq.iloc[-1] / eq.iloc[0] - 1) * 100) if len(eq) > 1 else 0.0,
        "cagr_pct": _cagr(eq),
        "max_drawdown_pct": _max_drawdown(eq),
        "sharpe": _sharpe(rets),
        "benchmark_return_pct": bench_ret,
        "days": len(eq),
        "open_positions_end": len(positions),
    }
