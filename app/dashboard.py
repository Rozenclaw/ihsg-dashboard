"""IHSG dashboard (Phases 1–3) — bilingual EN / ID, multipage.

Run:  streamlit run app/dashboard.py
Data comes from the local SQLite DB populated by scripts/refresh_data.py.

Thin entry point: shared sidebar + st.navigation across two pages. The widgets
live in the ``app/ui`` package:
  - ui.common          shared helpers, config, cached data accessors
  - ui.header          IHSG index header + live-quote panel
  - ui.recommendations Top-3, monthly stacking, recommendations table, alerts
  - ui.detail          price chart, watchlist table, news panel
  - ui.portfolio       paper portfolio, backtest, real-holdings tracker
  - ui.sidebar         language + data-refresh controls
  - ui.decision        Decision Helper page (daily/monthly + AI narrative)
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

# ui.common runs st.set_page_config on import (first st call).
from ui.common import (CFG, LANG, T, _conv_badge, db, divcal, explain, fmt,  # noqa: E402
                       get_recommendations, st, strength_radar, theme,
                       top3_symbols)
from ui.header import index_header, live_panel  # noqa: E402
from ui.recommendations import (alerts_section, recommendations_section,  # noqa: E402
                                stacking_section, top3_section)
from ui.detail import news_panel, price_chart, watchlist_table  # noqa: E402
from ui.portfolio import (backtest_section, paper_portfolio_section,  # noqa: E402
                          portfolio_section)
from ui.sidebar import sidebar_data_controls  # noqa: E402
from ui import decision as decision_page  # noqa: E402
from ui import daytrade as daytrade_page  # noqa: E402


def render_dashboard():
    """Main dashboard — an animated aurora hero over a stack of premium
    dropdown sections (key ones open, the rest collapsed for a clean view)."""
    theme.hero(st, T("app.title"), T("app.subtitle"), badge="LIVE")

    all_syms = db.list_symbols(include_index=False)
    # Default watchlist = today's Top 3 BUY picks (auto). Falls back to the
    # configured list, then the first few symbols, if there are no BUYs today.
    _top3 = [s for s in top3_symbols() if s in all_syms]
    default_wl = (_top3
                  or [s for s in CFG["dashboard"]["default_watchlist"] if s in all_syms]
                  or all_syms[:10])
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = default_wl

    # ---- KEY sections (open on load) ----
    with st.expander("📊  " + T("index.title"), expanded=True):
        index_header()

    with st.expander("🏆  " + T("top3.title"), expanded=True):
        top3_section()

    with st.expander("🔭  " + T("detail.title"), expanded=True):
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
                # Live recommendation row (trap, conviction, cum-date, radar).
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
                    st.plotly_chart(strength_radar({**fund, **rowd}))
                with rc2:
                    news_panel(sel)
            price_chart(sel)
        else:
            st.warning("Database empty. Run `python scripts/refresh_data.py` first.")

    # ---- Secondary sections (collapsed; click to expand) ----
    with st.expander("👁️  " + T("wl.title"), expanded=False):
        watch = st.multiselect(T("wl.tickers"), options=all_syms, key="watchlist",
                               label_visibility="collapsed")
        watchlist_table(watch)
        st.divider()
        live_panel(watch)

    with st.expander("🔔  " + T("alert.title"), expanded=False):
        alerts_section(all_syms)

    with st.expander("🧱  " + T("stack.title"), expanded=False):
        stacking_section()

    with st.expander("📋  " + T("rec.title"), expanded=False):
        recommendations_section()

    with st.expander("💼  " + T("port.title"), expanded=False):
        portfolio_section(all_syms)

    with st.expander("🧪  " + T("paper.title") + "  ·  " + T("bt.title"), expanded=False):
        pcol, bcol = st.columns(2)
        with pcol:
            paper_portfolio_section()
        with bcol:
            backtest_section()


# ----------------------------- app shell --------------------------------

# Shared sidebar (language + data controls) renders on every page. Call it
# before navigation so LANG() reflects the chosen language in the nav titles.
sidebar_data_controls()

# Inject the cosmic-aurora premium theme + ornaments every rerun (idempotent).
# Rendered inside the sidebar so its invisible 0-px helper iframe stays out of
# the main column's entrance-stagger order. Runs on every page via this shell.
with st.sidebar:
    theme.inject(st)

# Explicit url_path for the non-default section pages: both modules expose a
# callable named `render`, so Streamlit would otherwise infer a duplicate path.
# The default dashboard must stay at the root path; Streamlit ignores url_path on
# default pages and shows a "Page not found" modal if /dashboard is opened.
_nav = st.navigation([
    st.Page(render_dashboard, title=T("nav.dashboard"), icon="📈", default=True),
    st.Page(daytrade_page.render, title=T("nav.daytrade"), icon="📊",
            url_path="daily-trading"),
    st.Page(decision_page.render, title=T("nav.decision"), icon="🧭",
            url_path="decision-helper"),
])
_nav.run()
