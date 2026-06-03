"""IHSG dashboard (Phases 1–3) — bilingual EN / ID.

Run:  streamlit run app/dashboard.py
Data comes from the local SQLite DB populated by scripts/refresh_data.py.

This file is the thin entry point: it wires the page layout together. The
actual widgets live in the ``app/ui`` package:
  - ui.common          shared helpers, config, cached data accessors
  - ui.header          IHSG index header + live-quote panel
  - ui.recommendations Top-3, monthly stacking, recommendations table, alerts
  - ui.detail          price chart, watchlist table, news panel
  - ui.portfolio       paper portfolio, backtest, real-holdings tracker
  - ui.sidebar         language + data-refresh controls
"""
from __future__ import annotations

import os
import sys

# Make both the project root and the app/ dir importable, regardless of how
# Streamlit launches this script.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ui.common runs st.set_page_config + theme.inject on import (first st call).
from ui.common import (CFG, LANG, T, _conv_badge, db, divcal, explain, fmt,  # noqa: E402
                       get_recommendations, st, strength_radar, top3_symbols)
from ui.header import index_header, live_panel  # noqa: E402
from ui.recommendations import (alerts_section, recommendations_section,  # noqa: E402
                                stacking_section, top3_section)
from ui.detail import news_panel, price_chart, watchlist_table  # noqa: E402
from ui.portfolio import (backtest_section, paper_portfolio_section,  # noqa: E402
                          portfolio_section)
from ui.sidebar import sidebar_data_controls  # noqa: E402


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
