"""Daily Trading page — liquid-universe SWING shortlist + budget allocation sim.

Ranks the stored universe into a daily-refreshed Top-N shortlist (BUY / WATCH /
AVOID) using src/daytrade.py, then lets the user enter a limited daily budget and
simulates a lot-aware allocation across the BUY picks — with NET gain/loss after
realistic costs. An optional AI "coach note" (risk-first persona) is gated behind
a button. Decision-support only — not financial advice.
"""
from __future__ import annotations

import os

from ui.common import (CFG, LANG, T, clean_ticker, fmt, pd, st, stock_table,
                       theme, ticker_hover)
from src import daytrade, airesearch  # noqa: E402  (path set up by ui.common)


def _api_key(cfg: dict) -> str | None:
    """Resolve the provider's API key from env vars first, then st.secrets."""
    for name in airesearch.key_env_names(cfg):
        val = os.environ.get(name)
        if val:
            return val
        try:
            if name in st.secrets:  # type: ignore[operator]
                return st.secrets[name]
        except Exception:
            pass
    return None


@st.cache_data(ttl=300, show_spinner=False)
def _board(lang: str, top_n: int) -> dict:
    """Cached shortlist build (scans the whole universe — ttl 5 min)."""
    return daytrade.build_board(CFG, lang=lang, top_n=top_n)


_SIG_STYLE = {"BUY": "color:#34d399;font-weight:700",
              "WATCH": "color:#fbbf24;font-weight:600",
              "AVOID": "color:#8a93a6"}


def render():
    method = daytrade._method_label(LANG())
    theme.hero(st, T("dt.title"), method["summary"], badge="DAILY")

    top_n = int(st.session_state.get("dt_top_n", 10))
    board = _board(LANG(), top_n)
    if not board["rows"]:
        st.warning(T("top3.none"))
        st.caption(T("dt.disclaimer"))
        return

    # --- summary KPI strip (always visible under the hero) ---
    c = board["counts"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T("dt.universe"), board["universe_count"])
    m2.metric(T("dt.buys"), c.get("BUY", 0))
    m3.metric(T("dt.watch_n"), c.get("WATCH", 0))
    m4.metric(T("dt.avoid_n"), c.get("AVOID", 0))
    st.info(T("dt.candidate_note"))

    with st.expander("ℹ️  " + T("nav.daytrade"), expanded=False):
        st.markdown(T("dt.explainer"))

    # --- the ranked shortlist (open) ---
    with st.expander("📋  " + T("dt.board_title", n=top_n), expanded=True):
        rows = board["rows"]
        _syms = [r["symbol"] for r in rows]
        board_df = pd.DataFrame([{
            "#": r["rank"], T("stack.colsym"): clean_ticker(r["symbol"]),
            T("dt.col_signal"): r["signal"],
            T("dt.col_score"): r["score"], "RSI": r["rsi"], "ATR%": r["atr_pct"],
            T("top3.entry"): r["entry"], T("top3.target"): r["target"],
            T("top3.stop"): r["stop"], T("dt.col_rr"): r["rr"], T("dt.col_risk"): r["stop_pct"],
        } for r in rows])
        _sigcol = T("dt.col_signal")

        def _sigstyle(col, v, rd):
            return _SIG_STYLE.get(v, "") if col == _sigcol else ""

        stock_table(board_df, symbol_col=T("stack.colsym"), raw_symbols=_syms,
                    cell_style=_sigstyle, fmt={
            T("dt.col_score"): "{:.0f}", "RSI": "{:.0f}", "ATR%": "{:.1f}%",
            T("top3.entry"): "{:,.0f}", T("top3.target"): "{:,.0f}", T("top3.stop"): "{:,.0f}",
            T("dt.col_rr"): "{:.2f}x", T("dt.col_risk"): "{:.1f}%",
        })

        # short "why" for the actionable (BUY / WATCH) names
        actionable = [r for r in rows if r["signal"] in ("BUY", "WATCH")]
        if actionable:
            for r in actionable[:5]:
                st.caption(f"{ticker_hover(r['symbol'])} ({r['signal']}) — "
                           + " · ".join(r["why"]), unsafe_allow_html=True)
        st.caption(T("dt.cost_warn", pct=f"{board['breakeven_pct']:.2f}"))

    # --- daily budget allocation simulation (open) ---
    with st.expander("🧮  " + T("dt.sim_title"), expanded=True):
        s1, s2, s3 = st.columns(3)
        capital = s1.number_input(
            T("dt.capital"), min_value=500_000.0,
            value=max(500_000.0, float(board["params"].get("default_capital_idr", 10_000_000))),
            step=1_000_000.0, format="%.0f", key="dt_capital")
        budget = s2.number_input(
            T("dt.budget"), min_value=100_000.0,
            value=max(100_000.0, float(board["params"].get("default_daily_budget_idr", 1_000_000))),
            step=100_000.0, format="%.0f", key="dt_budget")
        num = s3.selectbox(T("dt.num"), list(range(1, top_n + 1)), index=min(2, top_n - 1),
                           key="dt_num")
        include_watch = st.checkbox(T("dt.include_watch"), value=False, key="dt_watch")
        if budget > capital:
            st.warning(T("dt.budget_gt_capital"))

        sim = daytrade.simulate_allocation(board, float(budget), num=int(num),
                                           include_watch=include_watch,
                                           capital_idr=float(capital))
        if include_watch and any(r["signal"] == "WATCH" for r in sim["rows"]):
            st.caption("⚠️ " + T("dt.watch_used"))

        if not sim["rows"]:
            st.info(sim["note"])
        else:
            t = sim["totals"]
            a, b, d, e = st.columns(4)
            a.metric(T("dt.spent"), fmt(sim["spent"]))
            b.metric(T("dt.leftover"), fmt(sim["leftover"]))
            d.metric(T("dt.net_gain"), fmt(t["gain"]))
            e.metric(T("dt.net_loss"), fmt(t["loss"]))
            g, h = st.columns(2)
            g.metric(T("dt.net_rr"), f"{fmt(t['rr'], 2)}x" if t.get("rr") else "—")
            if t.get("risk_pct_capital") is not None:
                h.metric(T("dt.risk_vs_capital"), f"{fmt(t['risk_pct_capital'], 2)}%")
            if t.get("risk_warn"):
                st.warning(T("dt.risk_warn", pct=fmt(t["risk_pct_capital"], 2),
                             cap=fmt(t.get("risk_warn_pct"), 1)))

            _asyms = [r["symbol"] for r in sim["rows"]]
            alloc_df = pd.DataFrame([{
                T("stack.colsym"): clean_ticker(r["symbol"]), T("dt.col_signal"): r["signal"],
                T("dt.col_lots"): r["lots"], T("dt.col_shares"): r["shares"],
                T("dt.col_capital"): r["capital"], T("dt.col_weight"): r["pct"],
                T("top3.entry"): r["entry"], T("top3.stop"): r["stop"],
                T("top3.target"): r["target"], T("dt.net_gain"): r["gain"],
                T("dt.net_loss"): r["loss"],
            } for r in sim["rows"]])
            stock_table(alloc_df, symbol_col=T("stack.colsym"), raw_symbols=_asyms,
                        cell_style=_sigstyle, fmt={
                T("dt.col_shares"): "{:,.0f}", T("dt.col_capital"): "{:,.0f}",
                T("dt.col_weight"): "{:.0f}%", T("top3.entry"): "{:,.0f}",
                T("top3.stop"): "{:,.0f}", T("top3.target"): "{:,.0f}",
                T("dt.net_gain"): "{:,.0f}", T("dt.net_loss"): "{:,.0f}",
            })
            if sim.get("note"):
                st.caption(sim["note"])

    # --- beginner rules + honest caveats (collapsed) ---
    with st.expander("📏  " + T("dt.tips_title") + "  ·  " + T("dt.caveats_title"),
                     expanded=False):
        t1, t2 = st.columns(2)
        with t1:
            st.markdown(f"##### {T('dt.tips_title')}")
            st.markdown(T("dt.tips"))
        with t2:
            st.markdown(f"##### {T('dt.caveats_title')}")
            st.markdown(T("dt.caveats"))

    # --- optional AI coach note (collapsed; gated button; risk-first persona) ---
    with st.expander("🤖  " + T("dt.ai_title"), expanded=False):
        aicfg = CFG.get("ai", {}) or {}
        key = _api_key(aicfg)
        ai_ok, why = airesearch.available(aicfg, key)
        cache_key = f"dt_ai::{LANG()}::{top_n}::{board['as_of']}::{budget}::{num}::{include_watch}"

        b1, b2 = st.columns([1, 2])
        gen = b1.button(T("dt.gen_ai"), disabled=not ai_ok, width="stretch",
                        key="dt_gen", type="primary")
        if not ai_ok:
            b2.caption("⚠️ " + T("dh.ai_unavail", why=why))

        narrative = st.session_state.get(cache_key)
        if gen:
            facts = daytrade.to_markdown(board, sim)
            with st.spinner(T("dt.ai_spinner")):
                result = airesearch.narrate({}, aicfg, lang=LANG(), api_key=key,
                                             facts=facts, system=airesearch.SYSTEM_DAYTRADE)
            if result:
                narrative = result
                st.session_state[cache_key] = result
            else:
                st.warning(T("dh.ai_failed"))

        if narrative:
            st.caption(T("dt.ai_on"))
            st.markdown(narrative)
            st.download_button(T("dh.download"), data=narrative,
                               file_name=f"daily_trading_{board['as_of']}.md",
                               mime="text/markdown", key="dt_dl")
        elif ai_ok:
            st.caption(T("dt.press_hint"))

    st.caption(T("dt.disclaimer"))
