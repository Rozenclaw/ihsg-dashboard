"""Recommendation-driven sections: Top-3 picks, monthly stacking allocator,
the full recommendations table, and the price/RSI alerts manager."""
from __future__ import annotations

import pandas as pd

from ui.common import (CFG, LANG, T, _conv_badge, allocate, clean_ticker, db,
                       divcal, explain, fmt, get_recommendations, nojk, st,
                       stock_chip, stock_table, ticker_hover, top3_symbols)


def top3_section():
    """Highlighted Top-3 BUY picks to stack (accumulate) today, with reasons."""
    df = get_recommendations()
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
            st.markdown(
                f"<div style='font-size:1.1rem;font-weight:800;display:flex;"
                f"align-items:center;gap:8px;margin:.1rem 0 .35rem;'>{medals[i]} "
                f"{stock_chip(r['symbol'], size=26)}</div>", unsafe_allow_html=True)
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
            st.caption(f"**{T('top3.why')}:** " + nojk(explain.why_today(r.to_dict(), LANG())))
            if r.get("yield_trap"):
                st.warning(nojk(explain.trap_note(r.to_dict(), LANG())))


def stacking_section():
    scfg = CFG.get("stacking", {})
    default_budget = float(scfg.get("monthly_budget_idr", 5_000_000))
    default_n = int(scfg.get("num_stocks", 3))
    default_entry = bool(scfg.get("use_entry_price", True))

    month_name = pd.Timestamp.today().strftime("%B %Y")
    st.caption(f"{T('stack.caption')} · {T('stack.this_month')}: **{month_name}**")

    # Settings tucked away in a popover — the default just uses your saved budget.
    with st.popover(f"⚙️ {T('stack.advanced')}"):
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
            st.markdown(
                f"<div style='font-size:1.05rem;font-weight:800;display:flex;"
                f"align-items:center;gap:8px;margin:.1rem 0 .35rem;'>{medals[i]} "
                f"{stock_chip(r['symbol'], size=24)}</div>", unsafe_allow_html=True)
            st.metric(f"{r['lots']} lot · {r['shares']:,} shares",
                      fmt(r["cost"], 0),
                      f"{r['pct']:.0f}% · {fmt(r.get('div_yield_pct'),2)}% yield"
                      if r.get("div_yield_pct") is not None else f"{r['pct']:.0f}%")
            st.caption(f"@ {fmt(r['price'],0)} / share")

    # Detail table
    syms = [r["symbol"] for r in pl["rows"]]
    rows = [{
        T("stack.colsym"): clean_ticker(r["symbol"]),
        T("stack.collots"): r["lots"],
        T("stack.colshares"): r["shares"],
        T("stack.colprice"): r["price"],
        T("stack.colcost"): r["cost"],
        T("stack.colpct"): r["pct"],
        T("stack.colyield"): r.get("div_yield_pct"),
    } for r in pl["rows"]]
    dff = pd.DataFrame(rows)
    stock_table(dff, symbol_col=T("stack.colsym"), raw_symbols=syms, fmt={
        T("stack.colprice"): "{:,.0f}", T("stack.colcost"): "{:,.0f}",
        T("stack.colpct"): "{:.0f}%", T("stack.colyield"): "{:.2f}",
        T("stack.colshares"): "{:,.0f}", T("stack.collots"): "{:.0f}",
    })

    st.caption("🛒 " + T("stack.howto"))
    if pl["note"]:
        st.caption("ℹ️ " + pl["note"])
    st.caption(T("rec.disclaimer"))


def recommendations_section():
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
                     disabled=not buy_up, width="stretch"):
            current = set(st.session_state.get("watchlist", []))
            added = [s for s in buy_up if s not in current]
            current.update(buy_up)
            st.session_state["watchlist"] = sorted(current)
            st.toast(T("rec.added_toast", n=len(added)) if added
                     else T("rec.already_toast"))
            st.rerun()
    with b2:
        if buy_up:
            st.caption("BUY + uptrend: "
                       + ", ".join(ticker_hover(s, bold=False) for s in buy_up[:12])
                       + (" …" if len(buy_up) > 12 else ""),
                       unsafe_allow_html=True)
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

    _syms = view["symbol"].tolist()
    view["symbol"] = [clean_ticker(s) for s in _syms]

    def _rowbg(col, v, rd):
        c = {"BUY": "rgba(6,78,59,0.5)", "SELL": "rgba(127,29,29,0.5)",
             "HOLD": "rgba(31,41,55,0.55)"}.get(rd.get("action"), "")
        return f"background:{c};" if c else ""

    stock_table(view, symbol_col="symbol", raw_symbols=_syms, cell_style=_rowbg, fmt={
        "Score": "{:.0f}", "Fund": "{:.0f}", "Tech": "{:.0f}", "Yield%": "{:.2f}",
        "rsi": "{:.0f}", "SectorRank%": "{:.0f}", "Days→cum": "{:.0f}",
        "entry": "{:,.0f}", "target": "{:,.0f}",
        "stop": "{:,.0f}", "lots": "{:.0f}", "Est cost (IDR)": "{:,.0f}",
    }, max_height=400)

    buy_hold = view[view["action"].isin(["BUY", "HOLD", "SELL"])]
    if not buy_hold.empty:
        with st.expander(T("rec.explain_q")):
            # view["symbol"] is now the CLEAN ticker; match it back to the raw
            # df symbol (BBRI -> BBRI.JK) before looking up the explanation.
            for _, r in buy_hold.head(12).iterrows():
                m = df[df["symbol"].map(clean_ticker) == r["symbol"]]
                if m.empty:
                    continue
                st.markdown("- " + nojk(explain.explain_recommendation(
                    m.iloc[0].to_dict(), LANG())))
    st.caption(T("rec.disclaimer"))


def alerts_section(all_syms: list[str]):
    st.caption(T("alert.caption"))
    with st.form("add_alert", clear_on_submit=True):
        a1, a2, a3, a4 = st.columns([2, 1, 1, 1])
        sym = a1.selectbox(T("alert.symbol"), options=all_syms, key="al_sym",
                           format_func=clean_ticker)
        metric = a2.selectbox(T("alert.metric"), ["price", "rsi"], key="al_metric")
        op = a3.selectbox(T("alert.op"), ["below", "above"], key="al_op")
        thr = a4.number_input(T("alert.threshold"), value=0.0, step=1.0, key="al_thr")
        note = st.text_input(T("alert.note"), key="al_note")
        if st.form_submit_button(T("alert.add"), width="stretch"):
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
                f"{ticker_hover(a['symbol'])} · {a['metric'].upper()} {a['op']} "
                f"{a['threshold']:,.0f}" + (f" · _{a['note']}_" if a['note'] else "")
                + (f"  \n_last fired: {a['last_fired']}_" if a['last_fired'] else ""),
                unsafe_allow_html=True)
            if cols[1].button("🗑", key=f"del_{a['id']}"):
                db.delete_alert(a["id"])
                st.rerun()

    if st.button(T("alert.check_now"), width="stretch"):
        from src import alerts as _al
        trig = _al.check_alerts(CFG, fire=False)  # dry-run preview, don't dedupe
        if trig:
            for t in trig:
                st.success(nojk(_al.format_alert(t)))
        else:
            st.info(T("alert.none_triggered"))
