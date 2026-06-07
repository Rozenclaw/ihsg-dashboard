"""Shared dashboard plumbing: page config, theme, config, formatting helpers,
cached data accessors, and small chart utilities.

Importing this module also runs ``st.set_page_config`` + ``theme.inject`` once
(first Streamlit call), and re-exports the ``src`` modules so section modules
can ``from ui.common import db, explain, ...`` without their own path setup.
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go  # noqa: F401  (re-exported)
import streamlit as st
from plotly.subplots import make_subplots  # noqa: F401  (re-exported)

# Make the project root importable regardless of how Streamlit launches us.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Re-exported for section modules (from ui.common import db, explain, ...);
# flagged "unused" locally but consumed by importers.
from src import (db, indicators, live, strategy, explain, paper,  # noqa: E402,F401
                 backtest, i18n, divcal, portfolio, news, theme, allocate)
from src.config import get_config  # noqa: E402

# Plotly template tuned to the cosmic-aurora glass theme: transparent bg so the
# aurora backdrop shows through the chart's glass frame, soft grid, Inter.
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#cdd6e6", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)"),
    colorway=["#818CF8", "#38E1F0", "#C084FC", "#34D399", "#FB7185"],
)

# Time-range presets for the IHSG hero + stock detail (label -> calendar window).
RANGES = ["1D", "7D", "30D", "YTD", "1Y", "5Y"]

# --- First Streamlit calls: page config + config (run once on import) ---
# Theming (dark palette + MacBook-Air density) is set natively in
# .streamlit/config.toml — Streamlit 1.50's sanitizer drops large injected
# <style> blocks, so config is the reliable channel. See src/theme.py.
st.set_page_config(page_title="IHSG Dashboard", layout="wide", page_icon="📈")
CFG = get_config()


def _style_fig(fig):
    """Apply the glass-theme layout to any Plotly figure."""
    fig.update_layout(**PLOTLY_LAYOUT)
    try:
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    except Exception:
        pass
    return fig


def fmt(x, dp=0):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.{dp}f}"


def LANG() -> str:
    return st.session_state.get("lang", "EN")


def T(key: str, **kw) -> str:
    """Translate a UI string into the current language."""
    return i18n.t(key, LANG(), **kw)


def _conv_badge(conviction: str) -> str:
    return {"high": "🟢 " + T("conv.high"),
            "medium": "🟡 " + T("conv.medium"),
            "speculative": "🟠 " + T("conv.speculative")}.get(conviction, "")


@st.cache_data(ttl=300)
def get_enriched(symbol: str) -> pd.DataFrame:
    return indicators.enrich(db.load_prices(symbol), CFG)


@st.cache_data(ttl=300)
def get_recommendations() -> pd.DataFrame:
    recs = strategy.evaluate_universe(CFG)
    return pd.DataFrame([r.as_row() for r in recs])


# Cache live quotes for a short window so repeated reruns (interactions, the
# auto-refresh fragment, language toggle, …) reuse ONE provider call instead of
# re-hitting Yahoo/iTick each time. TTL from config live.cache_seconds, clamped
# to 60-120s. Keyed by the symbol set; the Refresh button clears all caches.
_LIVE_TTL = max(60, min(120, int((CFG.get("live") or {}).get("cache_seconds", 90))))


@st.cache_data(ttl=_LIVE_TTL, show_spinner=False)
def get_live_quotes(symbols: tuple) -> dict:
    return live.fetch_quotes(list(symbols), cfg=CFG)


def top3_symbols() -> list[str]:
    """Today's best 3 BUY picks (uptrend-first, then composite). Empty if none."""
    df = get_recommendations()
    if df.empty:
        return []
    buys = df[df["action"] == "BUY"].copy()
    if buys.empty:
        return []
    buys["_up"] = buys["trend"].isin(["Uptrend", "Above SMA"]).astype(int)
    buys = buys.sort_values(["_up", "composite"], ascending=[False, False])
    return buys["symbol"].head(3).tolist()


def _slice_range(df: pd.DataFrame, rng: str) -> pd.DataFrame:
    """Return the tail of df for the chosen range. Indicators are computed on
    the full history first, so SMA/RSI/Bollinger stay correct after slicing."""
    if df.empty:
        return df
    end = df.index.max()
    if rng == "1D":
        start = end - pd.Timedelta(days=2)      # last 1–2 sessions
    elif rng == "7D":
        start = end - pd.Timedelta(days=7)
    elif rng == "30D":
        start = end - pd.Timedelta(days=30)
    elif rng == "YTD":
        start = pd.Timestamp(year=end.year, month=1, day=1)
    elif rng == "1Y":
        start = end - pd.DateOffset(years=1)
    elif rng == "5Y":
        start = end - pd.DateOffset(years=5)
    else:
        return df
    return df[df.index >= start]


def _period_metrics(view: pd.DataFrame) -> dict:
    """Return summary stats for the visible window."""
    if view.empty or len(view) < 1:
        return {}
    first = float(view["close"].iloc[0])
    last = float(view["close"].iloc[-1])
    chg = ((last - first) / first * 100) if first else None
    return {
        "change_pct": chg,
        "high": float(view["high"].max()),
        "low": float(view["low"].min()),
        "avg_vol": float(view["volume"].mean()) if "volume" in view else None,
        "bars": len(view),
    }


def strength_radar(row: dict):
    """Snowflake-style 5-axis radar of a stock's strengths (0..100)."""
    def _val(pe, pb):
        s = 0.0
        if isinstance(pe, (int, float)) and pe > 0:
            s += max(0, min(50, (25 - pe) / (25 - 8) * 50))
        if isinstance(pb, (int, float)) and pb > 0:
            s += max(0, min(50, (3 - pb) / (3 - 0.8) * 50))
        return s
    dy = row.get("div_yield_pct") or 0
    rsi = row.get("rsi")
    axes = {
        "Dividend": max(0, min(100, dy / 10 * 100)),
        "Value": _val(row.get("pe"), row.get("pb")),
        "Quality": max(0, min(100, (row.get("roe") or 0) / 20 * 100)),
        "Momentum": (100 - abs((rsi or 50) - 55) / 55 * 100) if rsi is not None else 50,
        "Trend": 100 if row.get("trend") in ("Uptrend", "Above SMA") else 25,
    }
    cats = list(axes.keys()) + [list(axes.keys())[0]]
    vals = list(axes.values()) + [list(axes.values())[0]]
    fig = go.Figure(go.Scatterpolar(r=vals, theta=cats, fill="toself",
                                    line=dict(color="#818CF8", width=2),
                                    fillcolor="rgba(129,140,248,0.20)"))
    fig.update_layout(height=230, margin=dict(l=28, r=28, t=28, b=16),
                      polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(visible=True, range=[0, 100],
                                                 showticklabels=False,
                                                 gridcolor="rgba(255,255,255,0.08)"),
                                 angularaxis=dict(gridcolor="rgba(255,255,255,0.08)")),
                      showlegend=False, title=T("radar.title"))
    return _style_fig(fig)
