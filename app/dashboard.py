"""IHSG dashboard (Phases 1–3) — bilingual EN / ID.

Run:  streamlit run app/dashboard.py
Data comes from the local SQLite DB populated by scripts/refresh_data.py.
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import (db, indicators, live, strategy, explain, paper,  # noqa: E402
                 backtest, i18n, divcal, portfolio, news, theme, allocate)
from src.config import get_config  # noqa: E402

# Plotly template tuned to the glass theme: transparent bg, soft grid, Inter.
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#cdd6e6", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.08)"),
    colorway=["#5eead4", "#818cf8", "#f472b6", "#fbbf24", "#34d399"],
)


def _style_fig(fig):
    """Apply the glass-theme layout to any Plotly figure."""
    fig.update_layout(**PLOTLY_LAYOUT)
    try:
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    except Exception:
        pass
    return fig


def _conv_badge(conviction: str) -> str:
    return {"high": "🟢 " + T("conv.high"),
            "medium": "🟡 " + T("conv.medium"),
            "speculative": "🟠 " + T("conv.speculative")}.get(conviction, "")


def strength_radar(row: dict):
    """Snowflake-style 5-axis radar of a stock's strengths (0..100)."""
    import plotly.graph_objects as go

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
                                    line=dict(color="#5eead4", width=2),
                                    fillcolor="rgba(94,234,212,0.18)"))
    fig.update_layout(height=260, margin=dict(l=30, r=30, t=30, b=20),
                      polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(visible=True, range=[0, 100],
                                                 showticklabels=False,
                                                 gridcolor="rgba(255,255,255,0.08)"),
                                 angularaxis=dict(gridcolor="rgba(255,255,255,0.08)")),
                      showlegend=False, title=T("radar.title"))
    return _style_fig(fig)

st.set_page_config(page_title="IHSG Dashboard", layout="wide", page_icon="📈")
theme.inject(st)   # premium dark liquid-glass styling
CFG = get_config()


def fmt(x, dp=0):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.{dp}f}"


def LANG() -> str:
    return st.session_state.get("lang", "EN")


def T(key: str, **kw) -> str:
    """Translate a UI string into the current language."""
    return i18n.t(key, LANG(), **kw)


@st.cache_data(ttl=300)
def get_enriched(symbol: str) -> pd.DataFrame:
    return indicators.enrich(db.load_prices(symbol), CFG)


@st.cache_data(ttl=300)
def get_recommendations() -> pd.DataFrame:
    recs = strategy.evaluate_universe(CFG)
    return pd.DataFrame([r.as_row() for r in recs])


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


# ----------------------------- index header -----------------------------

def _ihsg_hero_chart(df: pd.DataFrame, rng: str):
    """Premium animated IHSG area chart with crosshair + rich cursor tooltip."""
    view = _slice_range(df, rng)
    if view.empty:
        view = df.tail(2)
    close = view["close"]
    rising = float(close.iloc[-1]) >= float(close.iloc[0]) if len(close) > 1 else True
    line_c = "#34d399" if rising else "#fb7185"       # green up / rose down
    fill_c = "rgba(52,211,153,0.14)" if rising else "rgba(251,113,133,0.12)"

    # daily % change for the tooltip
    chg = close.pct_change() * 100
    base = float(close.iloc[0]) if len(close) else 0.0
    cum = (close / base - 1) * 100 if base else close * 0
    customdata = list(zip(chg.fillna(0).round(2), cum.round(2),
                          view["high"], view["low"],
                          (view["volume"] if "volume" in view else close * 0)))

    fig = go.Figure()
    # soft glow underlayer
    fig.add_trace(go.Scatter(
        x=view.index, y=close, mode="lines",
        line=dict(color=line_c, width=6), opacity=0.18, hoverinfo="skip",
        showlegend=False))
    # main animated line + gradient fill
    fig.add_trace(go.Scatter(
        x=view.index, y=close, mode="lines", name="IHSG",
        line=dict(color=line_c, width=2.4, shape="spline", smoothing=0.6),
        fill="tozeroy", fillcolor=fill_c, customdata=customdata,
        hovertemplate=(
            "<b>%{x|%a, %d %b %Y}</b><br>"
            "Level: <b>%{y:,.0f}</b><br>"
            "Day: %{customdata[0]:+.2f}%  ·  Since start: %{customdata[1]:+.2f}%<br>"
            "High %{customdata[2]:,.0f} · Low %{customdata[3]:,.0f}"
            "<extra></extra>"),
        showlegend=False))
    # marker dot on the latest point
    fig.add_trace(go.Scatter(
        x=[view.index[-1]], y=[float(close.iloc[-1])], mode="markers",
        marker=dict(size=10, color=line_c, line=dict(color="white", width=1.5)),
        hoverinfo="skip", showlegend=False))

    # y padding for breathing room
    lo, hi = float(close.min()), float(close.max())
    pad = (hi - lo) * 0.12 if hi > lo else hi * 0.02
    fig.update_layout(
        height=360, margin=dict(l=8, r=8, t=10, b=8),
        hovermode="x unified",
        xaxis=dict(showspikes=True, spikemode="across", spikethickness=1,
                   spikedash="dot", spikecolor="rgba(255,255,255,0.35)",
                   showgrid=False, rangeslider=dict(visible=False)),
        yaxis=dict(range=[lo - pad, hi + pad], showspikes=True,
                   spikethickness=1, spikedash="dot",
                   spikecolor="rgba(255,255,255,0.2)"),
        transition=dict(duration=600, easing="cubic-in-out"),
        hoverlabel=dict(bgcolor="rgba(18,26,40,0.92)", bordercolor=line_c,
                        font=dict(family="Inter", size=13, color="#e8edf4")),
    )
    return _style_fig(fig)


def index_header():
    df = get_enriched(CFG["data"]["index_symbol"])
    st.markdown(f"### {T('index.title')}")
    if df.empty:
        st.warning(T("index.no_data"))
        return
    snap = indicators.snapshot(df, CFG)

    # KPI row (glass metric cards)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T("index.level"), fmt(snap["close"], 2),
              f"{fmt(snap['change_pct'], 2)}%" if snap["change_pct"] is not None else None)
    c2.metric("RSI(14)", fmt(snap["rsi"], 1))
    c3.metric(T("index.trend"), snap["trend"])
    c4.metric(T("index.range_pos"), f"{fmt(snap['range_pos_pct'], 0)}%")

    # Range toggle + animated hero chart
    rng = st.radio(T("range.label"), RANGES, index=4, horizontal=True,
                   key="ihsg_range", label_visibility="collapsed")
    pm = _period_metrics(_slice_range(df, rng))
    if pm and pm.get("change_pct") is not None:
        arrow = "▲" if pm["change_pct"] >= 0 else "▼"
        color = "#34d399" if pm["change_pct"] >= 0 else "#fb7185"
        st.markdown(
            f"<div style='font-size:.92rem; color:#9aa7bd; margin:-2px 0 6px;'>"
            f"<b style='color:{color}'>{arrow} {pm['change_pct']:+.2f}%</b> "
            f"{T('range.return')} · {rng} · "
            f"{T('range.high')} {pm['high']:,.0f} · {T('range.low')} {pm['low']:,.0f}"
            f"</div>", unsafe_allow_html=True)
    st.plotly_chart(_ihsg_hero_chart(df, rng), use_container_width=True,
                    config={"displayModeBar": False, "scrollZoom": False})

    with st.expander(T("index.explain_q")):
        st.markdown(explain.explain_index(snap, LANG()))
    last = db.last_refresh()
    if last:
        st.caption(f"{T('side.last_pull')}: {last['run_at']} UTC · "
                   f"{last['source']} · {last['symbols']} symbols · {last['status']}")


# ----------------------------- live panel -------------------------------

def _live_panel_body(symbols: list[str]):
    lcfg = CFG.get("live", {})
    syms = symbols[: lcfg.get("max_symbols", 15)]
    if not live.get_token():
        st.info(T("live.no_token"))
        return
    if not syms:
        st.caption("—")
        return
    quotes = live.fetch_quotes(syms)
    rows, errors = [], []
    for sym in syms:
        q = quotes.get(sym, {})
        if q.get("ok"):
            last, op = q.get("last"), q.get("open")
            chg = ((last - op) / op * 100) if (last and op) else None
            rows.append({"Symbol": sym, "Last": last, "Open": op,
                         "High": q.get("high"), "Low": q.get("low"),
                         "Chg % (vs open)": chg, "Volume": q.get("volume")})
        else:
            errors.append(f"{sym}: {q.get('error') or 'no data'}")
    if rows:
        dfq = pd.DataFrame(rows)
        st.dataframe(dfq.style.format({
            "Last": "{:,.0f}", "Open": "{:,.0f}", "High": "{:,.0f}", "Low": "{:,.0f}",
            "Chg % (vs open)": "{:+.2f}", "Volume": "{:,.0f}",
        }, na_rep="—"), use_container_width=True, hide_index=True)
        st.caption(f"Live · iTick · {T('live.updated')} "
                   f"{pd.Timestamp.now().strftime('%H:%M:%S')} · "
                   f"{lcfg.get('poll_seconds', 60)}s · IDX ~09:00–16:00 WIB")
    if errors:
        with st.expander(f"{len(errors)} quote issue(s)"):
            for e in errors:
                st.text(e)


def live_panel(symbols: list[str]):
    lcfg = CFG.get("live", {})
    if not lcfg.get("enabled", True):
        return
    st.markdown(f"#### {T('live.title')}")
    poll = int(lcfg.get("poll_seconds", 60))
    frag = getattr(st, "fragment", None)
    if frag is not None:
        @st.fragment(run_every=poll)
        def _auto():
            _live_panel_body(symbols)
        _auto()
    else:
        if st.button("↻"):
            pass
        _live_panel_body(symbols)


# ----------------------------- price chart ------------------------------

# Time-range presets for the stock detail (label -> calendar window).
RANGES = ["1D", "7D", "30D", "YTD", "1Y", "5Y"]


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


def price_chart(symbol: str):
    df = get_enriched(symbol)
    if df.empty:
        st.info(f"No data for {symbol}.")
        return
    snap = indicators.snapshot(df, CFG)
    st.info(explain.explain_stock(snap, CFG, symbol, LANG()))

    # --- Time-range toggle ---
    rng = st.radio(T("range.label"), RANGES, index=4, horizontal=True,
                   key=f"range_{symbol}", label_visibility="collapsed")
    view = _slice_range(df, rng)
    if view.empty:
        st.caption(T("range.no_data"))
        view = df.tail(2)
    pm = _period_metrics(view)
    if pm:
        g1, g2, g3, g4 = st.columns(4)
        delta = f"{pm['change_pct']:+.2f}%" if pm.get("change_pct") is not None else None
        g1.metric(f"{rng} {T('range.return')}", delta or "—")
        g2.metric(f"{rng} {T('range.high')}", fmt(pm["high"], 0))
        g3.metric(f"{rng} {T('range.low')}", fmt(pm["low"], 0))
        g4.metric(T("range.avg_vol"), fmt(pm.get("avg_vol"), 0))

    ind = CFG["indicators"]
    fast, slow = f"sma{ind['sma_fast']}", f"sma{ind['sma_slow']}"
    df = view  # chart the selected window (indicators already computed on full data)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28],
                        vertical_spacing=0.04,
                        subplot_titles=(f"{symbol} · {rng}", "RSI(14)"))
    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"],
                                 low=df["low"], close=df["close"], name="OHLC"), row=1, col=1)
    for col, color in [(fast, "#2563eb"), (slow, "#f59e0b")]:
        if col in df:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col.upper(),
                                     line=dict(width=1.2, color=color)), row=1, col=1)
    if "bb_upper" in df:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], name="BB upper",
                                 line=dict(width=0.7, color="#9ca3af"), opacity=0.5), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], name="BB lower",
                                 line=dict(width=0.7, color="#9ca3af"), opacity=0.5,
                                 fill="tonexty", fillcolor="rgba(156,163,175,0.08)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI",
                             line=dict(width=1.2, color="#7c3aed")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)
    try:
        lo, hi = float(df["low"].min()), float(df["high"].max())
        if hi > lo:
            pad = (hi - lo) * 0.08
            fig.update_yaxes(range=[max(0, lo - pad), hi + pad], row=1, col=1)
    except Exception:
        pass
    fig.update_layout(height=620, margin=dict(l=10, r=10, t=40, b=10),
                      xaxis_rangeslider_visible=False, showlegend=True,
                      legend=dict(orientation="h", y=1.02))
    _style_fig(fig)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander(T("chart.howto_q")):
        st.markdown(explain.legend_help(LANG()))


# ----------------------------- recommendations --------------------------

def top3_section():
    """Highlighted Top-3 BUY picks to stack (accumulate) today, with reasons."""
    df = get_recommendations()
    st.markdown(f"### {T('top3.title')}")
    last = db.last_refresh()
    asof = last["run_at"][:10] if last else pd.Timestamp.today().strftime("%Y-%m-%d")
    st.caption(f"{T('top3.caption')} · {T('top3.as_of')} {asof}")
    if df.empty:
        st.warning(T("rec.no_data"))
        return
    syms = top3_symbols()
    if not syms:
        st.info(T("top3.none"))
        return
    buys = df[df["symbol"].isin(syms)].set_index("symbol").loc[syms].reset_index()

    medals = ["🥇", "🥈", "🥉"]
    cols = st.columns(3)
    for i, (_, r) in enumerate(buys.iterrows()):
        with cols[i]:
            st.markdown(f"#### {medals[i]} {r['symbol']}")
            st.metric(f"Score · Yield", f"{fmt(r['composite'],0)}/100",
                      f"{fmt(r['div_yield_pct'],2)}% yield" if pd.notna(r['div_yield_pct']) else None)
            ent, tgt, stp = r.get("entry"), r.get("target"), r.get("stop")
            lots = r.get("lots")
            st.markdown(
                f"**{T('top3.entry')}:** {fmt(ent,0)}  \n"
                f"**{T('top3.target')}:** {fmt(tgt,0)}  \n"
                f"**{T('top3.stop')}:** {fmt(stp,0)}"
                + (f"  \n**{T('top3.size')}:** {int(lots)} lot" if pd.notna(lots) and lots else ""))
            conv = _conv_badge(r.get("conviction", ""))
            cum = divcal.label(r.get("ex_dividend_date"), LANG())
            if conv:
                st.markdown(conv)
            if cum and cum != "—":
                st.caption(f"📅 {cum}")
            st.caption(f"**{T('top3.why')}:** " + explain.why_today(r.to_dict(), LANG()))
            if r.get("yield_trap"):
                st.warning(explain.trap_note(r.to_dict(), LANG()))


def stacking_section():
    scfg = CFG.get("stacking", {})
    default_budget = float(scfg.get("monthly_budget_idr", 5_000_000))
    default_n = int(scfg.get("num_stocks", 3))
    default_entry = bool(scfg.get("use_entry_price", True))

    st.markdown(f"### {T('stack.title')}")
    month_name = pd.Timestamp.today().strftime("%B %Y")
    st.caption(f"{T('stack.caption')} · {T('stack.this_month')}: **{month_name}**")

    # Settings tucked away — the default just uses your saved monthly budget.
    with st.expander(f"⚙️ {T('stack.advanced')}"):
        c1, c2, c3 = st.columns([2, 1, 2])
        budget = c1.number_input(T("stack.budget"), min_value=100_000.0,
                                 value=default_budget, step=500_000.0, format="%.0f")
        n = c2.selectbox(T("stack.names"), [1, 2, 3, 4, 5],
                         index=[1, 2, 3, 4, 5].index(default_n) if default_n in (1,2,3,4,5) else 2)
        use_entry = c3.toggle(T("stack.use_entry"), value=default_entry)
        st.caption(f"💡 Saved default: {default_budget:,.0f} IDR / month across "
                   f"{default_n} stocks. Edit `config.yaml → stacking` to change permanently.")

    df = get_recommendations()
    pl = allocate.plan(budget, df, max_names=int(n), use_entry=use_entry)

    if not pl["rows"]:
        st.info(pl["note"] or T("top3.none"))
        return

    # Headline: budget summary
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T("stack.budget"), fmt(pl["budget"], 0))
    m2.metric(T("stack.spent"), fmt(pl["spent"], 0),
              f"{pl['spent']/pl['budget']*100:.0f}%")
    m3.metric(T("stack.leftover"), fmt(pl["leftover"], 0))
    m4.metric(T("stack.picks"), pl["picks"])

    # Medal cards — the "Top 3 monthly buying list"
    medals = ["🥇", "🥈", "🥉", "④", "⑤"]
    cols = st.columns(len(pl["rows"]))
    for i, r in enumerate(pl["rows"]):
        with cols[i]:
            st.markdown(f"#### {medals[i]} {r['symbol']}")
            st.metric(f"{r['lots']} lot · {r['shares']:,} shares",
                      fmt(r["cost"], 0),
                      f"{r['pct']:.0f}% · {fmt(r.get('div_yield_pct'),2)}% yield"
                      if r.get("div_yield_pct") is not None else f"{r['pct']:.0f}%")
            st.caption(f"@ {fmt(r['price'],0)} / share")

    # Detail table
    rows = [{
        T("stack.colsym"): r["symbol"],
        T("stack.collots"): r["lots"],
        T("stack.colshares"): r["shares"],
        T("stack.colprice"): r["price"],
        T("stack.colcost"): r["cost"],
        T("stack.colpct"): r["pct"],
        T("stack.colyield"): r.get("div_yield_pct"),
    } for r in pl["rows"]]
    dff = pd.DataFrame(rows)
    st.dataframe(dff.style.format({
        T("stack.colprice"): "{:,.0f}", T("stack.colcost"): "{:,.0f}",
        T("stack.colpct"): "{:.0f}%", T("stack.colyield"): "{:.2f}",
        T("stack.colshares"): "{:,.0f}", T("stack.collots"): "{:.0f}",
    }, na_rep="—"), use_container_width=True, hide_index=True)

    st.caption("🛒 " + T("stack.howto"))
    if pl["note"]:
        st.caption("ℹ️ " + pl["note"])
    st.caption(T("rec.disclaimer"))


def recommendations_section():
    st.markdown(f"### {T('rec.title')}")
    st.caption(T("rec.caption"))
    df = get_recommendations()
    if df.empty:
        st.warning(T("rec.no_data"))
        return
    c1, c2, c3, c4 = st.columns(4)
    counts = df["action"].value_counts().to_dict()
    c1.metric("BUY", counts.get("BUY", 0))
    c2.metric("HOLD", counts.get("HOLD", 0))
    c3.metric("SELL", counts.get("SELL", 0))
    c4.metric(T("rec.universe"), len(df))

    buy_up = df[(df["action"] == "BUY") &
                (df["trend"].isin(["Uptrend", "Above SMA"]))]["symbol"].tolist()
    b1, b2 = st.columns([2, 3])
    with b1:
        if st.button(T("rec.add_buy_uptrend", n=len(buy_up)),
                     disabled=not buy_up, use_container_width=True):
            current = set(st.session_state.get("watchlist", []))
            added = [s for s in buy_up if s not in current]
            current.update(buy_up)
            st.session_state["watchlist"] = sorted(current)
            st.toast(T("rec.added_toast", n=len(added)) if added
                     else T("rec.already_toast"))
            st.rerun()
    with b2:
        if buy_up:
            st.caption("BUY + uptrend: " + ", ".join(buy_up[:12]) +
                       (" …" if len(buy_up) > 12 else ""))
        else:
            st.caption(T("rec.none_buy_uptrend"))

    actions = st.multiselect(T("rec.show_actions"), ["BUY", "HOLD", "SELL", "SKIP"],
                             default=["BUY", "HOLD", "SELL"])
    view = df[df["action"].isin(actions)].copy()
    cols = ["symbol", "action", "conviction", "composite", "sector", "sector_rank_pct",
            "fundamental_score", "technical_score", "div_yield_pct", "rsi", "trend",
            "days_to_cum", "entry", "target", "stop", "lots", "est_cost_idr"]
    cols = [c for c in cols if c in view.columns]
    view = view[cols].rename(columns={
        "composite": "Score", "fundamental_score": "Fund", "technical_score": "Tech",
        "div_yield_pct": "Yield%", "sector_rank_pct": "SectorRank%",
        "days_to_cum": "Days→cum", "est_cost_idr": "Est cost (IDR)",
        "conviction": "Conv",
    })

    def _highlight(row):
        color = {"BUY": "#064e3b", "SELL": "#7f1d1d", "HOLD": "#1f2937"}.get(row["action"], "")
        return [f"background-color: {color}" if color else ""] * len(row)

    st.dataframe(view.style.apply(_highlight, axis=1).format({
        "Score": "{:.0f}", "Fund": "{:.0f}", "Tech": "{:.0f}", "Yield%": "{:.2f}",
        "rsi": "{:.0f}", "SectorRank%": "{:.0f}", "Days→cum": "{:.0f}",
        "entry": "{:,.0f}", "target": "{:,.0f}",
        "stop": "{:,.0f}", "lots": "{:.0f}", "Est cost (IDR)": "{:,.0f}",
    }, na_rep="—"), use_container_width=True, hide_index=True, height=460)

    buy_hold = view[view["action"].isin(["BUY", "HOLD", "SELL"])]
    if not buy_hold.empty:
        with st.expander(T("rec.explain_q")):
            for _, r in buy_hold.head(12).iterrows():
                st.markdown("- " + explain.explain_recommendation(
                    df[df["symbol"] == r["symbol"]].iloc[0].to_dict(), LANG()))
    st.caption(T("rec.disclaimer"))


# ----------------------------- watchlist --------------------------------

def alerts_section(all_syms: list[str]):
    st.markdown(f"#### {T('alert.title')}")
    st.caption(T("alert.caption"))
    with st.form("add_alert", clear_on_submit=True):
        a1, a2, a3, a4 = st.columns([2, 1, 1, 1])
        sym = a1.selectbox(T("alert.symbol"), options=all_syms, key="al_sym")
        metric = a2.selectbox(T("alert.metric"), ["price", "rsi"], key="al_metric")
        op = a3.selectbox(T("alert.op"), ["below", "above"], key="al_op")
        thr = a4.number_input(T("alert.threshold"), value=0.0, step=1.0, key="al_thr")
        note = st.text_input(T("alert.note"), key="al_note")
        if st.form_submit_button(T("alert.add"), use_container_width=True):
            if thr:
                db.add_alert(sym, metric, op, thr, note)
                st.toast(T("alert.added"))
                st.rerun()

    rows = db.list_alerts()
    if not rows:
        st.caption(T("alert.none"))
    else:
        for a in rows:
            cols = st.columns([5, 1])
            cols[0].markdown(
                f"**{a['symbol']}** · {a['metric'].upper()} {a['op']} "
                f"{a['threshold']:,.0f}" + (f" · _{a['note']}_" if a['note'] else "")
                + (f"  \n_last fired: {a['last_fired']}_" if a['last_fired'] else ""))
            if cols[1].button("🗑", key=f"del_{a['id']}"):
                db.delete_alert(a["id"])
                st.rerun()

    if st.button(T("alert.check_now"), use_container_width=True):
        from src import alerts as _al
        trig = _al.check_alerts(CFG, fire=False)  # dry-run preview, don't dedupe
        if trig:
            for t in trig:
                st.success(_al.format_alert(t))
        else:
            st.info(T("alert.none_triggered"))


def watchlist_table(symbols: list[str]):
    rows = []
    for sym in symbols:
        df = get_enriched(sym)
        if df.empty:
            continue
        s = indicators.snapshot(df, CFG)
        fund = db.load_fundamentals(sym)
        price = s["close"]
        div = fund.get("last_dividend")
        dy = (div / price * 100) if (div and price) else None
        rows.append({"Symbol": sym, "Close": price, "Chg %": s["change_pct"],
                     "RSI": s["rsi"], "Trend": s["trend"],
                     "Range pos %": s["range_pos_pct"], "Div yield %": dy})
    if not rows:
        st.warning(T("wl.no_data"))
        return
    dfw = pd.DataFrame(rows)
    st.dataframe(dfw.style.format({
        "Close": "{:,.0f}", "Chg %": "{:+.2f}", "RSI": "{:.0f}",
        "Range pos %": "{:.0f}", "Div yield %": "{:.2f}",
    }, na_rep="—"), use_container_width=True, hide_index=True)


# ----------------------------- paper portfolio --------------------------

def paper_portfolio_section():
    st.markdown(f"### {T('paper.title')}")
    st.caption(T("paper.caption"))
    snap = paper.portfolio_snapshot(CFG)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T("paper.equity"), fmt(snap["equity"], 0),
              f"{snap['total_return_pct']:+.1f}%" if snap["start_equity"] else None)
    c2.metric(T("paper.cash"), fmt(snap["cash"], 0))
    c3.metric(T("paper.holdings"), fmt(snap["holdings"], 0))
    c4.metric(T("paper.positions"), len(snap["rows"]))

    b1, b2 = st.columns(2)
    with b1:
        if st.button(T("paper.advance"), use_container_width=True):
            res = paper.run_day(CFG)
            st.cache_data.clear()
            st.toast("Paper day: " + (", ".join(res["actions"]) or "no trades"))
            st.rerun()
    with b2:
        if st.button(T("paper.reset"), use_container_width=True):
            paper.reset(CFG)
            st.cache_data.clear()
            st.toast("Reset")
            st.rerun()

    if snap["rows"]:
        dfp = pd.DataFrame(snap["rows"])
        st.dataframe(dfp.style.format({
            "Avg price": "{:,.0f}", "Last": "{:,.0f}", "Market value": "{:,.0f}",
            "Unreal P/L": "{:,.0f}", "Unreal P/L %": "{:+.1f}",
            "Target": "{:,.0f}", "Stop": "{:,.0f}", "Lots": "{:.0f}",
        }, na_rep="—"), use_container_width=True, hide_index=True)
    else:
        st.info(T("paper.no_pos"))

    eq = db.load_equity_curve()
    if len(eq) > 1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=eq["date"], y=eq["equity"], name="Equity",
                                 line=dict(color="#5eead4", width=2),
                                 fill="tozeroy", fillcolor="rgba(94,234,212,0.08)"))
        fig.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10),
                          showlegend=False, title="Equity curve")
        _style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)
    trades = db.load_trades()
    if not trades.empty:
        with st.expander(f"Trade history ({len(trades)})"):
            st.dataframe(trades, use_container_width=True, hide_index=True)


# ----------------------------- backtest ---------------------------------

@st.cache_data(ttl=1800)
def _run_backtest(lookback: int, rebalance: int, maxpos: int) -> dict:
    res = backtest.run(CFG, lookback_days=lookback, rebalance_every=rebalance,
                       max_positions=maxpos)
    if "equity" in res and hasattr(res["equity"], "reset_index"):
        res = dict(res)
        edf = res["equity"].reset_index()
        edf.columns = ["date", "equity"]
        res["equity_df"] = edf
        del res["equity"]
    return res


def backtest_section():
    st.markdown(f"### {T('bt.title')}")
    st.caption(T("bt.caption"))
    c1, c2, c3, c4 = st.columns(4)
    lookback = c1.selectbox(T("bt.lookback"), [126, 252, 504, 756], index=2)
    rebalance = c2.selectbox(T("bt.rebalance"), [1, 5, 10, 20], index=1)
    maxpos = c3.selectbox(T("bt.maxpos"), [5, 8, 10, 15], index=2)
    run = c4.button(T("bt.run"), use_container_width=True)
    if not run:
        st.info(T("bt.set_params"))
        return
    with st.spinner("…"):
        res = _run_backtest(lookback, rebalance, maxpos)
    if "error" in res:
        st.warning(f"Backtest error: {res['error']}")
        return
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T("bt.total_return"), f"{res['total_return_pct']:+.1f}%")
    m2.metric("CAGR", f"{res['cagr_pct']:+.1f}%")
    m3.metric(T("bt.maxdd"), f"{res['max_drawdown_pct']:.1f}%")
    m4.metric("Sharpe", f"{res['sharpe']:.2f}")
    if res.get("benchmark_return_pct") is not None:
        beat = res["total_return_pct"] > res["benchmark_return_pct"]
        st.markdown(f"**IHSG buy & hold:** {res['benchmark_return_pct']:+.1f}% — "
                    f"strategy **{'beat' if beat else 'lagged'}** benchmark.")
    if "equity_df" in res and len(res["equity_df"]) > 1:
        edf = res["equity_df"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edf["date"], y=edf["equity"], name="Strategy",
                                 line=dict(color="#818cf8", width=2),
                                 fill="tozeroy", fillcolor="rgba(129,140,248,0.08)"))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10),
                          showlegend=False, title="Backtest equity curve")
        _style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)


# ----------------------------- sidebar ----------------------------------

def news_panel(symbol: str):
    st.markdown(f"**{T('news.title')}**")
    data = news.get_news(symbol)
    items = data.get("items", [])
    if not items:
        st.caption(T("news.none"))
        return
    badge = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}[data["overall"]]
    st.caption(f"{T('news.overall')}: {badge} {data['overall']}")
    for it in items[:5]:
        s = it.get("score", 0)
        dot = "🟢" if s > 0 else ("🔴" if s < 0 else "⚪")
        title = it["title"]
        if it.get("link"):
            st.markdown(f"{dot} [{title}]({it['link']})  \n<small>{it.get('publisher','')}</small>",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"{dot} {title}  \n<small>{it.get('publisher','')}</small>",
                        unsafe_allow_html=True)


def portfolio_section(all_syms: list[str]):
    st.markdown(f"### {T('port.title')}")
    st.caption(T("port.caption"))
    with st.expander("➕ Import / paste holdings (CSV)"):
        sample = "symbol,lots,avg_price,note\nBBRI,10,4100,core\nPTBA,5,2800,dividend"
        text = st.text_area("CSV", value="", placeholder=sample, height=120,
                            label_visibility="collapsed")
        ci1, ci2 = st.columns(2)
        if ci1.button(T("port.import"), use_container_width=True):
            n, errs = portfolio.import_csv(text, replace=True)
            st.cache_data.clear()
            if n:
                st.toast(f"Imported {n} holdings")
            if errs:
                st.warning("; ".join(errs[:4]))
            st.rerun()
        if ci2.button(T("port.clear"), use_container_width=True):
            db.clear_holdings()
            st.cache_data.clear()
            st.rerun()

    snap = portfolio.snapshot(CFG)
    if not snap["rows"]:
        st.info(T("port.none"))
        return
    m1, m2, m3 = st.columns(3)
    m1.metric(T("port.value"), fmt(snap["value"], 0))
    m2.metric(T("port.cost"), fmt(snap["cost"], 0))
    m3.metric(T("port.pl"), fmt(snap["pl"], 0), f"{snap['pl_pct']:+.1f}%")
    if snap["sell_flags"]:
        st.warning(T("port.sell_warn") + ", ".join(snap["sell_flags"]))
    dfh = pd.DataFrame(snap["rows"])
    st.dataframe(dfh.style.format({
        "Avg price": "{:,.0f}", "Last": "{:,.0f}", "Cost": "{:,.0f}",
        "Value": "{:,.0f}", "P/L": "{:,.0f}", "P/L %": "{:+.1f}", "Lots": "{:.0f}",
    }, na_rep="—"), use_container_width=True, hide_index=True)


def sidebar_data_controls():
    import datetime as _dt
    from src import fetch

    st.sidebar.radio(
        i18n.t("side.language", LANG()), options=["EN", "ID"],
        format_func=lambda c: "🇬🇧 English" if c == "EN" else "🇮🇩 Bahasa Indonesia",
        key="lang", horizontal=True)
    st.sidebar.divider()

    st.sidebar.header(T("side.data"))
    last = db.last_refresh()
    if last:
        st.sidebar.caption(f"{T('side.last_pull')}: {last['run_at']} UTC\n\n"
                           f"{last['source']} · {last['symbols']} · {last['status']}")
    else:
        st.sidebar.caption(T("side.no_data"))

    if st.sidebar.button(T("side.refresh_now"), use_container_width=True, type="primary"):
        with st.spinner(T("side.refreshing")):
            try:
                summary = fetch.refresh(full_universe=False, with_fundamentals=True,
                                        verbose=False)
                st.cache_data.clear()
                st.sidebar.success(f"Updated {summary['ok']} ({summary['rows']} rows).")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Refresh failed: {e}")

    st.sidebar.divider()
    auto = st.sidebar.toggle(T("side.auto_refresh"), value=False)
    interval_min = st.sidebar.select_slider(
        T("side.every"), options=[15, 30, 60, 120, 240], value=60,
        disabled=not auto, format_func=lambda m: f"{m} min")
    if auto:
        now = _dt.datetime.utcnow()
        key = "last_auto_refresh"
        prev = st.session_state.get(key)
        if prev is None or (now - prev).total_seconds() >= interval_min * 60:
            st.session_state[key] = now
            try:
                fetch.refresh(full_universe=False, with_fundamentals=True, verbose=False)
                st.cache_data.clear()
            except Exception:
                pass
        nxt = st.session_state[key] + _dt.timedelta(minutes=interval_min)
        st.sidebar.caption(f"Next ~{nxt.strftime('%H:%M')} UTC")
        frag = getattr(st, "fragment", None)
        if frag is not None:
            @st.fragment(run_every=min(interval_min * 60, 300))
            def _tick():
                st.empty()
            _tick()

    st.sidebar.divider()
    st.sidebar.caption(T("side.best_practice"))


# ----------------------------- layout -----------------------------------

sidebar_data_controls()

st.markdown(
    f"""<div style="display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
        margin-bottom:2px;">
      <span style="font-size:2.4rem; font-weight:800; letter-spacing:-0.03em;
        background:linear-gradient(120deg,#fff 0%,#5eead4 55%,#818cf8 100%);
        -webkit-background-clip:text; background-clip:text;
        -webkit-text-fill-color:transparent;">{T('app.title')}</span>
      <span style="display:inline-flex; align-items:center; gap:6px;
        padding:3px 12px; border-radius:999px; font-size:.72rem; font-weight:600;
        color:#5eead4; background:rgba(94,234,212,0.10);
        border:1px solid rgba(94,234,212,0.30);">
        <span style="width:7px;height:7px;border-radius:50%;background:#5eead4;
          box-shadow:0 0 8px #5eead4; display:inline-block;
          animation:pulse 1.8s infinite;"></span> LIVE</span>
    </div>
    <div style="color:#9aa7bd; font-size:.9rem; margin-bottom:6px;">{T('app.subtitle')}</div>
    <style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}</style>""",
    unsafe_allow_html=True)

index_header()
st.divider()

all_syms = db.list_symbols(include_index=False)
# Default watchlist = today's Top 3 BUY picks (auto). Falls back to the configured
# list, then to the first few symbols, if there are no BUYs today.
_top3 = [s for s in top3_symbols() if s in all_syms]
default_wl = (_top3
              or [s for s in CFG["dashboard"]["default_watchlist"] if s in all_syms]
              or all_syms[:10])
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = default_wl

top3_section()
st.divider()

stacking_section()
st.divider()

recommendations_section()
st.divider()

left, right = st.columns([1, 2])
with left:
    st.markdown(f"#### {T('wl.title')}")
    watch = st.multiselect(T("wl.tickers"), options=all_syms, key="watchlist",
                           label_visibility="collapsed")
    watchlist_table(watch)
    st.divider()
    live_panel(watch)
    st.divider()
    alerts_section(all_syms)
with right:
    st.markdown(f"#### {T('detail.title')}")
    if all_syms:
        sel = st.selectbox(T("detail.symbol"), options=all_syms,
                           index=all_syms.index(default_wl[0]) if default_wl else 0)
        fund = db.load_fundamentals(sel)
        if fund:
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Sector", fund.get("sector") or "—")
            d2.metric("P/E", fmt(fund.get("pe"), 1))
            d3.metric("P/B", fmt(fund.get("pb"), 2))
            d4.metric("ROE", f"{fmt(fund.get('roe'),0)}%" if fund.get("roe") is not None else "—")
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Div yield", f"{fmt(fund.get('dividend_yield'),2)}%"
                      if fund.get("dividend_yield") is not None else "—")
            e2.metric("Payout", f"{fmt(fund.get('payout_ratio'),0)}%"
                      if fund.get("payout_ratio") is not None else "—")
            e3.metric("Earnings growth", f"{fmt(fund.get('earnings_growth'),0)}%"
                      if fund.get("earnings_growth") is not None else "—")
            e4.metric("Beta", fmt(fund.get("beta"), 2))
            # Live recommendation row for this symbol (trap, conviction, cum-date, radar).
            _recs = get_recommendations()
            _row = _recs[_recs["symbol"] == sel]
            rowd = _row.iloc[0].to_dict() if not _row.empty else {}
            cum = divcal.label(fund.get("ex_dividend_date"), LANG())
            if cum and cum != "—":
                st.caption(f"📅 {T('cum.label')}: {cum}")
            if rowd.get("conviction"):
                st.caption(_conv_badge(rowd["conviction"]))
            if rowd.get("yield_trap"):
                st.warning(explain.trap_note(rowd, LANG()))
            rc1, rc2 = st.columns([1, 1])
            with rc1:
                st.plotly_chart(strength_radar({**fund, **rowd}),
                                use_container_width=True)
            with rc2:
                news_panel(sel)
        price_chart(sel)
    else:
        st.warning("Database empty. Run `python scripts/refresh_data.py` first.")


# Real-holdings section spans full width below the columns.
st.divider()
portfolio_section(all_syms)

st.divider()
pcol, bcol = st.columns(2)
with pcol:
    paper_portfolio_section()
with bcol:
    backtest_section()
