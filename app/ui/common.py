"""Shared dashboard plumbing: page config, theme, config, formatting helpers,
cached data accessors, and small chart utilities.

Importing this module also runs ``st.set_page_config`` + ``theme.inject`` once
(first Streamlit call), and re-exports the ``src`` modules so section modules
can ``from ui.common import db, explain, ...`` without their own path setup.
"""
from __future__ import annotations

import base64
import html as _html
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


# --------------------------------------------------------------------------- #
# Stock branding: clean ticker (no ".JK"), company name (hover), logo chip.    #
# --------------------------------------------------------------------------- #
_ASSETS_LOGOS = os.path.join(_ROOT, "assets", "logos")


def clean_ticker(symbol: str) -> str:
    """'BBRI.JK' -> 'BBRI' for DISPLAY only (the real symbol keeps the suffix)."""
    return str(symbol).split(".")[0]


def nojk(text: str) -> str:
    """Strip the '.JK' suffix from any prose/explanation shown to the user
    (the suffix only ever appears as an IDX ticker suffix, so this is safe)."""
    return str(text).replace(".JK", "")


@st.cache_data(ttl=3600)
def _company_names() -> dict:
    try:
        return db.load_security_names()
    except Exception:
        return {}


def company_name(symbol: str) -> str:
    """Full company name for a symbol (falls back to the clean ticker)."""
    return _company_names().get(symbol) or clean_ticker(symbol)


@st.cache_data(ttl=3600)
def logo_uri(symbol: str):
    """base64 data URI of the downloaded logo (assets/logos/TICKER.png), or None.
    Data URI so it embeds in inline HTML / ImageColumn without static serving."""
    p = os.path.join(_ASSETS_LOGOS, f"{clean_ticker(symbol)}.png")
    if os.path.exists(p):
        try:
            with open(p, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode()
        except Exception:
            return None
    return None


def _monogram_uri(symbol: str) -> str:
    """Inline SVG data URI: ticker initials on the aurora gradient (logo fallback)."""
    tk = clean_ticker(symbol)
    ini = _html.escape(tk[:2].upper())
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'>"
        "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0' stop-color='#818CF8'/><stop offset='1' stop-color='#22D3EE'/>"
        "</linearGradient></defs>"
        "<rect width='64' height='64' rx='14' fill='url(#g)'/>"
        f"<text x='32' y='42' font-family='Inter,Arial' font-size='28' font-weight='800'"
        f" fill='#08080f' text-anchor='middle'>{ini}</text></svg>")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def logo_or_monogram(symbol: str) -> str:
    """Always returns an image data URI — the real logo if downloaded, else a
    gradient-monogram fallback (so every stock shows something consistent)."""
    return logo_uri(symbol) or _monogram_uri(symbol)


def logo_col(symbols) -> list:
    """List of logo data URIs for a dataframe ImageColumn (one per symbol)."""
    return [logo_or_monogram(s) for s in symbols]


def ticker_hover(symbol, *, bold: bool = True) -> str:
    """Inline ticker text (no logo) with the full company name on hover. For use
    in markdown/caption prose via unsafe_allow_html=True."""
    tk = clean_ticker(symbol)
    label = f"<b>{tk}</b>" if bold else tk
    return f'<span class="tkr" title="{_html.escape(company_name(symbol))}">{label}</span>'


def stock_table(df, *, symbol_col, raw_symbols, fmt=None, cell_style=None,
                logo_size: int = 20, max_height: int = 430) -> None:
    """Render a DataFrame as a glass HTML table where the `symbol_col` cell shows
    a logo + clean ticker with the full company name on HOVER (every other
    st.dataframe lacks per-cell tooltips). `fmt` maps column -> python format
    string; `cell_style(col, value, rowdict) -> css` adds per-cell inline style
    (row highlights, signal colours). `raw_symbols` aligns 1:1 with df rows."""
    fmt = fmt or {}
    cols = list(df.columns)
    head = "".join(
        f'<th class="{"lft" if c == symbol_col else "rgt"}">{_html.escape(str(c))}</th>'
        for c in cols)
    body = []
    for i, rd in enumerate(df.to_dict("records")):
        tds = []
        for c in cols:
            v = rd.get(c)
            extra = ""
            if cell_style:
                try:
                    extra = cell_style(c, v, rd) or ""
                except Exception:
                    extra = ""
            if c == symbol_col:
                cls, inner = "lft", stock_chip(raw_symbols[i], size=logo_size)
            else:
                cls = "rgt"
                na = v is None
                try:
                    na = na or bool(pd.isna(v))
                except Exception:
                    na = (v is None)
                if na:
                    inner = "—"
                elif c in fmt:
                    try:
                        inner = _html.escape(fmt[c].format(v))
                    except Exception:
                        inner = _html.escape(str(v))
                else:
                    inner = _html.escape(str(v))
            sattr = f' style="{extra}"' if extra else ""
            tds.append(f'<td class="{cls}"{sattr}>{inner}</td>')
        body.append(f"<tr>{''.join(tds)}</tr>")
    mh = f"max-height:{max_height}px;" if max_height else ""
    st.markdown(
        f'<div class="stk-wrap" style="{mh}"><table class="stk">'
        f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True)


def stock_chip(symbol, *, size: int = 22, bold: bool = True, hover: bool = True) -> str:
    """Inline-HTML chip: [logo] TICKER with the full company name on hover.
    Use inside st.markdown(..., unsafe_allow_html=True)."""
    tk = clean_ticker(symbol)
    title = f' title="{_html.escape(company_name(symbol))}"' if hover else ""
    img = (f'<img src="{logo_or_monogram(symbol)}" alt="" loading="lazy" '
           f'style="width:{size}px;height:{size}px;border-radius:6px;object-fit:contain;'
           f'background:rgba(255,255,255,0.92);padding:1px;flex:0 0 auto;'
           f'box-shadow:0 1px 4px rgba(0,0,0,0.4);">')
    label = f"<b>{tk}</b>" if bold else tk
    return (f'<span style="display:inline-flex;align-items:center;gap:8px;'
            f'vertical-align:middle;cursor:default;"{title}>{img}{label}</span>')


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
