"""Decision Helper page — daily / monthly BUY-stacking decision aid.

Renders the deterministic analysis from src/decision.py (ranking, risk-reward,
sector warnings, verdict) and offers an optional AI-written research narrative
(src/airesearch.py) that gracefully falls back to the built-in write-up.
"""
from __future__ import annotations

import os

from ui.common import (CFG, LANG, T, _conv_badge, clean_ticker, fmt,
                       get_recommendations, logo_col, pd, st, stock_chip, theme)
from src import decision, airesearch  # noqa: E402  (path set up by ui.common)


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


def render():
    theme.hero(st, T("dh.title"), T("dh.caption"), badge="DECIDE")

    # --- controls (drive everything; always visible) ---
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

    # --- summary metrics (always visible) ---
    t = analysis["totals"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T("dh.picks"), len(analysis["picks"]))
    m2.metric(T("dh.total_capital"), fmt(t.get("capital")))
    m3.metric(T("dh.total_gain"), fmt(t.get("gain")))
    m4.metric(T("dh.total_loss"), fmt(t.get("loss")))

    # --- ranking medal cards (open) ---
    with st.expander("🏅  " + T("dh.ranking"), expanded=True):
        medals = ["🥇", "🥈", "🥉", "④", "⑤"]
        cols = st.columns(len(analysis["picks"]))
        for i, p in enumerate(analysis["picks"]):
            with cols[i]:
                st.markdown(
                    f"<div style='font-size:1rem;font-weight:800;display:flex;"
                    f"align-items:center;gap:8px;margin:.1rem 0 .3rem;'>{medals[i]} "
                    f"{stock_chip(p['symbol'], size=24)}</div>", unsafe_allow_html=True)
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

    # --- risk / reward table (open) ---
    with st.expander("⚖️  " + T("dh.rr_table"), expanded=True):
        _psyms = [p["symbol"] for p in analysis["picks"]]
        rr_rows = [{
            T("stack.colsym"): clean_ticker(p["symbol"]),
            T("top3.entry"): p["entry"], T("top3.target"): p["target"],
            T("top3.stop"): p["stop"], T("dh.total_capital"): p["capital"],
            T("dh.total_gain"): p["gain"], T("dh.total_loss"): p["loss"],
            "R:R": p["rr"],
        } for p in analysis["picks"]]
        rr_df = pd.DataFrame(rr_rows)
        rr_df.insert(0, "", logo_col(_psyms))
        st.dataframe(rr_df.style.format({
            T("top3.entry"): "{:,.0f}", T("top3.target"): "{:,.0f}",
            T("top3.stop"): "{:,.0f}", T("dh.total_capital"): "{:,.0f}",
            T("dh.total_gain"): "{:,.0f}", T("dh.total_loss"): "{:,.0f}",
            "R:R": "{:.2f}x",
        }, na_rep="—"), width="stretch", hide_index=True,
            column_config={"": st.column_config.ImageColumn("")})

    # --- sector concentration (always-visible warnings) ---
    for g in analysis.get("sector_groups", []):
        st.warning(T("dh.sector_warn") + ", ".join(g["symbols"]) + f"  ·  {g['sector']}")

    # --- written analysis (AI optional, deterministic fallback; collapsed) ---
    with st.expander("📝  " + T("dh.full_report"), expanded=False):
        aicfg = CFG.get("ai", {}) or {}
        key = _api_key(aicfg)
        ai_ok, why = airesearch.available(aicfg, key)
        cache_key = f"dh_ai::{LANG()}::{mode}::{num}::{budget}"

        bcol1, bcol2 = st.columns([1, 2])
        gen = bcol1.button(T("dh.gen_ai"), disabled=not ai_ok, width="stretch",
                           key="dh_gen", type="primary")
        if not ai_ok:
            bcol2.caption("⚠️ " + T("dh.ai_unavail", why=why))

        narrative = st.session_state.get(cache_key)
        if gen:
            with st.spinner(T("dh.ai_spinner")):
                result = airesearch.narrate(analysis, aicfg, lang=LANG(), api_key=key)
            if result:
                narrative = result
                st.session_state[cache_key] = result
            else:
                st.warning(T("dh.ai_failed"))

        # Written analysis is shown only after the AI narrative is generated.
        if narrative:
            st.caption(T("dh.ai_on"))
            st.markdown(narrative)
            st.download_button(T("dh.download"), data=narrative,
                               file_name=f"decision_{mode}_{analysis['as_of']}.md",
                               mime="text/markdown", key="dh_dl")
        elif ai_ok:
            st.caption(T("dh.press_hint"))
    st.caption(T("rec.disclaimer"))
