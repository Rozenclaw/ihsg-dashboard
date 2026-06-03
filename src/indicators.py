"""Technical indicators computed with pandas/numpy (no external TA dependency)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - (100 / (1 + rs))
    out[avg_loss == 0] = 100.0
    return out


def bollinger(series: pd.Series, period: int = 20, n_std: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = mid + n_std * std
    lower = mid - n_std * std
    return lower, mid, upper


def enrich(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Add indicator columns to an OHLCV frame indexed by date."""
    if df is None or df.empty:
        return df
    out = df.copy()
    close = out["close"]
    ind = cfg.get("indicators", {})
    out[f"sma{ind.get('sma_fast', 50)}"] = sma(close, ind.get("sma_fast", 50))
    out[f"sma{ind.get('sma_slow', 200)}"] = sma(close, ind.get("sma_slow", 200))
    out["rsi"] = rsi(close, ind.get("rsi_period", 14))
    lo, mid, up = bollinger(close, ind.get("bb_period", 20), ind.get("bb_std", 2.0))
    out["bb_lower"], out["bb_mid"], out["bb_upper"] = lo, mid, up
    out["vol_avg20"] = out["volume"].rolling(20, min_periods=5).mean()
    return out


def snapshot(df_enriched: pd.DataFrame, cfg: dict) -> dict:
    """Latest-row summary used by the dashboard tables."""
    if df_enriched is None or df_enriched.empty:
        return {}
    last = df_enriched.iloc[-1]
    ind = cfg.get("indicators", {})
    fast = f"sma{ind.get('sma_fast', 50)}"
    slow = f"sma{ind.get('sma_slow', 200)}"
    close = float(last["close"]) if pd.notna(last["close"]) else None
    prev_close = float(df_enriched["close"].iloc[-2]) if len(df_enriched) > 1 else None
    chg_pct = ((close - prev_close) / prev_close * 100) if close and prev_close else None
    high_52 = float(df_enriched["close"].tail(252).max())
    low_52 = float(df_enriched["close"].tail(252).min())
    rng_pos = ((close - low_52) / (high_52 - low_52) * 100) if high_52 > low_52 else None

    trend = "—"
    if pd.notna(last.get(fast)) and pd.notna(last.get(slow)):
        trend = "Uptrend" if last[fast] >= last[slow] else "Downtrend"
    elif pd.notna(last.get(fast)) and close is not None:
        trend = "Above SMA" if close >= last[fast] else "Below SMA"

    return {
        "close": close,
        "change_pct": chg_pct,
        "rsi": float(last["rsi"]) if pd.notna(last.get("rsi")) else None,
        "sma_fast": float(last[fast]) if pd.notna(last.get(fast)) else None,
        "sma_slow": float(last[slow]) if pd.notna(last.get(slow)) else None,
        "bb_lower": float(last["bb_lower"]) if pd.notna(last.get("bb_lower")) else None,
        "trend": trend,
        "range52_low": low_52,
        "range52_high": high_52,
        "range_pos_pct": rng_pos,
        "volume": float(last["volume"]) if pd.notna(last.get("volume")) else None,
        "vol_avg20": float(last["vol_avg20"]) if pd.notna(last.get("vol_avg20")) else None,
    }
