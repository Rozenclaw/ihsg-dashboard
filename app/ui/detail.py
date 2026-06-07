"""Stock-detail widgets: the candlestick/RSI price chart, the watchlist table,
and the per-symbol news panel."""
from __future__ import annotations

from ui.common import (CFG, LANG, RANGES, T, _period_metrics, _slice_range,
                       _style_fig, clean_ticker, db, explain, fmt, get_enriched,
                       go, indicators, logo_col, make_subplots, news, nojk, st)


def price_chart(symbol: str):
    df = get_enriched(symbol)
    if df.empty:
        st.info(f"No data for {symbol}.")
        return
    snap = indicators.snapshot(df, CFG)
    st.info(nojk(explain.explain_stock(snap, CFG, symbol, LANG())))

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
                        subplot_titles=(f"{clean_ticker(symbol)} · {rng}", "RSI(14)"))
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
    fig.update_layout(height=500, margin=dict(l=10, r=10, t=36, b=8),
                      xaxis_rangeslider_visible=False, showlegend=True,
                      legend=dict(orientation="h", y=1.02))
    _style_fig(fig)
    st.plotly_chart(fig)
    with st.expander(T("chart.howto_q")):
        st.markdown(explain.legend_help(LANG()))


def watchlist_table(symbols: list[str]):
    rows, syms_ok = [], []
    for sym in symbols:
        df = get_enriched(sym)
        if df.empty:
            continue
        s = indicators.snapshot(df, CFG)
        fund = db.load_fundamentals(sym)
        price = s["close"]
        div = fund.get("last_dividend")
        dy = (div / price * 100) if (div and price) else None
        rows.append({"Symbol": clean_ticker(sym), "Close": price, "Chg %": s["change_pct"],
                     "RSI": s["rsi"], "Trend": s["trend"],
                     "Range pos %": s["range_pos_pct"], "Div yield %": dy})
        syms_ok.append(sym)
    if not rows:
        st.warning(T("wl.no_data"))
        return
    import pandas as pd
    dfw = pd.DataFrame(rows)
    dfw.insert(0, "", logo_col(syms_ok))
    st.dataframe(dfw.style.format({
        "Close": "{:,.0f}", "Chg %": "{:+.2f}", "RSI": "{:.0f}",
        "Range pos %": "{:.0f}", "Div yield %": "{:.2f}",
    }, na_rep="—"), width="stretch", hide_index=True,
        column_config={"": st.column_config.ImageColumn("")})


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
