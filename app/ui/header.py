"""IHSG index header (KPIs + animated hero chart) and the live-quote panel."""
from __future__ import annotations

import pandas as pd

from ui.common import (CFG, LANG, RANGES, T, _period_metrics, _slice_range,
                       _style_fig, clean_ticker, db, explain, fmt, get_enriched,
                       get_live_quotes, go, indicators, live, st, stock_table)


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
        height=300, margin=dict(l=8, r=8, t=8, b=6),
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
    st.plotly_chart(_ihsg_hero_chart(df, rng),
                    config={"displayModeBar": False, "scrollZoom": False})

    with st.expander(T("index.explain_q")):
        st.markdown(explain.explain_index(snap, LANG()))
    last = db.last_refresh()
    if last:
        st.caption(f"{T('side.last_pull')}: {last['run_at']} UTC · "
                   f"{last['source']} · {last['symbols']} symbols · {last['status']}")


def _live_panel_body(symbols: list[str]):
    lcfg = CFG.get("live", {})
    syms = symbols[: lcfg.get("max_symbols", 15)]
    if live.needs_token(CFG) and not live.get_token():
        st.info(T("live.no_token"))
        return
    if not syms:
        st.caption("—")
        return
    quotes = get_live_quotes(tuple(syms))
    rows, errors, ok_syms = [], [], []
    for sym in syms:
        q = quotes.get(sym, {})
        if q.get("ok"):
            last, op = q.get("last"), q.get("open")
            chg = ((last - op) / op * 100) if (last and op) else None
            rows.append({"Symbol": clean_ticker(sym), "Last": last, "Open": op,
                         "High": q.get("high"), "Low": q.get("low"),
                         "Chg % (vs open)": chg, "Volume": q.get("volume")})
            ok_syms.append(sym)
        else:
            errors.append(f"{clean_ticker(sym)}: {q.get('error') or 'no data'}")
    if rows:
        dfq = pd.DataFrame(rows)
        stock_table(dfq, symbol_col="Symbol", raw_symbols=ok_syms, fmt={
            "Last": "{:,.0f}", "Open": "{:,.0f}", "High": "{:,.0f}", "Low": "{:,.0f}",
            "Chg % (vs open)": "{:+.2f}", "Volume": "{:,.0f}",
        }, max_height=360)
        st.caption(f"{live.provider_label(CFG)} · {T('live.updated')} "
                   f"{pd.Timestamp.now().strftime('%H:%M:%S')} · "
                   f"IDX ~09:00–16:00 WIB")
    if errors:
        # If nothing came back at all (e.g. an auth/quota problem hits every
        # symbol, or the market is closed), surface the reason up-front instead
        # of hiding it in the expander.
        if not rows:
            st.warning(f"⚠️ {T('live.unavailable')} — {errors[0].split(': ', 1)[-1]}")
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
