"""Offline synthetic OHLCV generator.

Lets you smoke-test the full pipeline (DB -> indicators -> dashboard) with no
network access. Deterministic per symbol so results are reproducible.
NOT real data — for testing/demo only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import DataSource


def _period_to_days(period: str) -> int:
    period = (period or "2y").strip().lower()
    if period.endswith("y"):
        return int(float(period[:-1]) * 365)
    if period.endswith("mo"):
        return int(float(period[:-2]) * 30)
    if period.endswith("d"):
        return int(period[:-1])
    return 730


class SyntheticSource(DataSource):
    name = "synthetic"

    def history(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        days = _period_to_days(period)
        seed = abs(hash(symbol)) % (2**32)
        rng = np.random.default_rng(seed)

        # Business-day calendar ending today.
        idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=max(days // 7 * 5, 260))
        n = len(idx)

        base = 500 + (seed % 9000)                  # starting price per symbol
        drift = (rng.random() - 0.45) * 0.0006       # slight per-symbol drift
        vol = 0.012 + rng.random() * 0.02            # daily volatility
        shocks = rng.normal(drift, vol, n)
        # add a gentle cycle so RSI/Bollinger have structure
        cycle = 0.03 * np.sin(np.linspace(0, rng.integers(6, 14), n))
        close = base * np.exp(np.cumsum(shocks + cycle / n))

        close = pd.Series(close, index=idx)
        intraday = (rng.random(n) * 0.02 + 0.005)
        high = close * (1 + intraday)
        low = close * (1 - intraday)
        openp = close.shift(1).fillna(close.iloc[0])
        volume = pd.Series(rng.integers(5_000_000, 120_000_000, n), index=idx, dtype=float)

        df = pd.DataFrame({
            "open": openp.round(2), "high": high.round(2),
            "low": low.round(2), "close": close.round(2), "volume": volume,
        })
        return df

    def fundamentals(self, symbol: str) -> dict:
        seed = abs(hash(symbol)) % (2**32)
        rng = np.random.default_rng(seed)
        price = 500 + (seed % 9000)
        payout = round(30 + rng.random() * 90, 1)        # 30%–120% (some traps)
        sectors = ["Financials", "Energy", "Consumer Defensive", "Basic Materials",
                   "Industrials", "Communication", "Healthcare"]
        return {
            "price": float(price),
            "market_cap": float(price) * rng.integers(1e9, 5e10),
            "beta": round(0.4 + rng.random(), 3),
            "last_dividend": round(price * (0.02 + rng.random() * 0.08), 2),
            "range_52w": f"{round(price*0.8,2)}-{round(price*1.3,2)}",
            "sector": sectors[seed % len(sectors)],
            "industry": "Test",
            "pe": round(5 + rng.random() * 25, 1),
            "pb": round(0.5 + rng.random() * 4, 2),
            "roe": round(rng.random() * 30, 1),
            "debt_to_equity": round(rng.random() * 150, 1),
            "payout_ratio": payout,
            "earnings_growth": round((rng.random() - 0.4) * 50, 1),  # can be negative
            "dividend_yield": round((0.02 + rng.random() * 0.10) * 100, 2),
            "ex_dividend_date": (pd.Timestamp.today().normalize()
                                 + pd.Timedelta(days=int(rng.integers(2, 45)))
                                 ).strftime("%Y-%m-%d"),
            "updated_at": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def news(self, symbol: str, limit: int = 6) -> list[dict]:
        base = symbol.replace(".JK", "")
        samples = [
            (f"{base} reports quarterly results in line with estimates", "pos"),
            (f"Analysts maintain neutral view on {base}", "neu"),
            (f"{base} announces dividend distribution schedule", "pos"),
        ]
        return [{"title": t, "publisher": "Synthetic Wire", "link": "",
                 "ts": None, "_sent": s} for t, s in samples[:limit]]
