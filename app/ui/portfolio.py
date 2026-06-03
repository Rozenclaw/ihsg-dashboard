"""Portfolio sections: simulated paper portfolio, strategy backtest, and the
real-holdings tracker (CSV import)."""
from __future__ import annotations

import pandas as pd

from ui.common import (CFG, T, _style_fig, backtest, db, fmt, go, paper,
                       portfolio, st)


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
        fig.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10),
                          showlegend=False, title="Equity curve")
        _style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)
    trades = db.load_trades()
    if not trades.empty:
        with st.expander(f"Trade history ({len(trades)})"):
            st.dataframe(trades, use_container_width=True, hide_index=True)


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
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
                          showlegend=False, title="Backtest equity curve")
        _style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)


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
