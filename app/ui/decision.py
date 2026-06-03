"""Decision Helper page — daily / monthly BUY-stacking decision aid.

Renders the deterministic analysis from src/decision.py (ranking, risk-reward,
sector warnings, verdict) and offers an optional AI-written research narrative
(src/airesearch.py) that gracefully falls back to the built-in write-up.
"""
from __future__ import annotations

import os

from ui.common import (CFG, LANG, T, _conv_badge, fmt, get_recommendations,
                       pd, st)
from src import decision, airesearch  # noqa: E402  (path set up by ui.common)


def _api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("ANTHROPIC_API_KEY")  # type: ignore[union-attr]
    except Exception:
        return None


def render():
    st.markdown(f"## {T('dh.title')}")
    st.caption(T("dh.caption"))

    # --- controls ---
    daily_lbl, monthly_lbl = T("dh.daily"), T("dh.monthly")
    c1, c2, c3 = st.columns([2, 1, 2])
    mode_lbl = c1.radio(T("dh.mode"), [daily_lbl, monthly_lbl], horizontal=True,
                        key="dh_mode")
    mode = "daily" if mode_lbl == daily_lbl else "monthly"
    num = c2.selectbox(T("dh.num"), [1, 2, 3, 4, 5], index=2, key="dh_num")
    budget = None
    if mode == "monthly":
        default_budget = float(CFG.get("stacking", {}).get("monthly_budget_idr", 5_000_000))
        budget = c3.number_input(T("stack.budget"), min_value=100_000.0,
                                 value=default_budget, step=500_000.0,
                                 format="%.0f", key="dh_budget")

    df = get_recommendations()
    analysis = decision.build_analysis(CFG, df, mode=mode, budget=budget,
                                       num=int(num), lang=LANG())
    if not analysis["picks"]:
        st.warning(T("top3.none"))
        return

    # --- summary metrics ---
    t = analysis["totals"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T("dh.picks"), len(analysis["picks"]))
    m2.metric(T("dh.total_capital"), fmt(t.get("capital")))
    m3.metric(T("dh.total_gain"), fmt(t.get("gain")))
    m4.metric(T("dh.total_loss"), fmt(t.get("loss")))

    # --- ranking medal cards ---
    st.markdown(f"#### {T('dh.ranking')}")
    medals = ["🥇", "🥈", "🥉", "④", "⑤"]
    cols = st.columns(len(analysis["picks"]))
    for i, p in enumerate(analysis["picks"]):
        with cols[i]:
            st.markdown(f"##### {medals[i]} {p['symbol']}")
            st.metric("Score · Yield", f"{fmt(p['score'])}/100",
                      f"{fmt(p['yield'], 2)}% yield" if p["yield"] is not None else None)
            st.markdown(f"**{T('top3.entry')}:** {fmt(p['entry'])} · "
                        f"**{T('top3.target')}:** {fmt(p['target'])} · "
                        f"**{T('top3.stop')}:** {fmt(p['stop'])}")
            rr = f" · R:R {fmt(p['rr'], 2)}x" if p["rr"] is not None else ""
            st.caption(f"{p['lots']} lot{rr}")
            badge = _conv_badge(p.get("conviction", ""))
            if badge:
                st.caption(badge)
            if p.get("cum_note"):
                st.caption(f"📅 {p['cum_note']}")
            if p.get("yield_trap"):
                st.caption(T("trap.badge"))

    # --- risk / reward table ---
    st.markdown(f"#### {T('dh.rr_table')}")
    rr_rows = [{
        T("stack.colsym"): p["symbol"],
        T("top3.entry"): p["entry"], T("top3.target"): p["target"],
        T("top3.stop"): p["stop"], T("dh.total_capital"): p["capital"],
        T("dh.total_gain"): p["gain"], T("dh.total_loss"): p["loss"],
        "R:R": p["rr"],
    } for p in analysis["picks"]]
    st.dataframe(pd.DataFrame(rr_rows).style.format({
        T("top3.entry"): "{:,.0f}", T("top3.target"): "{:,.0f}",
        T("top3.stop"): "{:,.0f}", T("dh.total_capital"): "{:,.0f}",
        T("dh.total_gain"): "{:,.0f}", T("dh.total_loss"): "{:,.0f}",
        "R:R": "{:.2f}x",
    }, na_rep="—"), use_container_width=True, hide_index=True)

    # --- sector concentration ---
    for g in analysis.get("sector_groups", []):
        st.warning(T("dh.sector_warn") + ", ".join(g["symbols"]) + f"  ·  {g['sector']}")

    # --- written analysis (AI optional, deterministic fallback) ---
    st.markdown(f"#### {T('dh.full_report')}")
    ai_ok, why = airesearch.available(_api_key())
    cache_key = f"dh_ai::{LANG()}::{mode}::{num}::{budget}"

    bcol1, bcol2 = st.columns([1, 2])
    gen = bcol1.button(T("dh.gen_ai"), disabled=not ai_ok, use_container_width=True,
                       key="dh_gen", type="primary")
    if not ai_ok:
        bcol2.caption("⚠️ " + T("dh.ai_unavail", why=why))

    narrative = st.session_state.get(cache_key)
    if gen:
        aicfg = CFG.get("ai", {}) or {}
        with st.spinner(T("dh.ai_spinner")):
            narrative = airesearch.narrate(
                analysis, lang=LANG(), model=aicfg.get("model"),
                api_key=_api_key(), effort=str(aicfg.get("effort", "low")))
        if narrative:
            st.session_state[cache_key] = narrative
        else:
            st.info(T("dh.ai_failed"))

    if narrative:
        st.caption(T("dh.ai_on"))
        report_md = narrative
    else:
        st.caption(T("dh.det_on"))
        report_md = decision.to_markdown(analysis)

    st.markdown(report_md)
    st.download_button(T("dh.download"), data=report_md,
                       file_name=f"decision_{mode}_{analysis['as_of']}.md",
                       mime="text/markdown", key="dh_dl")
    st.caption(T("rec.disclaimer"))
