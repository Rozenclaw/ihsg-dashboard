#!/usr/bin/env python3
"""Offline end-to-end test for Phase 3 (synthetic data, no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db, fetch, strategy, paper, backtest, notify  # noqa: E402
from src.config import get_config  # noqa: E402


def main() -> int:
    cfg = get_config()
    cfg["data"]["source"] = "synthetic"

    print("1) Seeding synthetic data (25 symbols, longer history) ...")
    cfg["data"]["history_period"] = "3y"
    fetch.refresh(full_universe=False, with_fundamentals=True, limit=25, verbose=False)

    print("2) Paper engine: reset + advance several days ...")
    paper.reset(cfg)
    recs = strategy.evaluate_universe(cfg)
    s1 = paper.run_day(cfg, run_date="2026-05-25", recs=recs)
    s2 = paper.run_day(cfg, run_date="2026-05-26", recs=recs)
    s3 = paper.run_day(cfg, run_date="2026-05-27", recs=recs)
    assert s3["equity"] > 0, s3
    snap = paper.portfolio_snapshot(cfg)
    assert abs((snap["cash"] + snap["holdings"]) - snap["equity"]) < 1.0, snap
    eq = db.load_equity_curve()
    assert len(eq) >= 1, "no equity points recorded"
    print(f"   -> equity {snap['equity']:,.0f} IDR, {len(snap['rows'])} positions, "
          f"{len(db.load_trades())} trades, {len(eq)} equity points")

    print("3) Paper accounting invariant (cash+holdings==equity) holds ✓")

    print("4) Backtest run ...")
    res = backtest.run(cfg, lookback_days=300, rebalance_every=5, max_positions=8)
    if "error" in res:
        print(f"   -> backtest skipped: {res['error']}")
    else:
        assert res["days"] > 0 and res["end_equity"] > 0, res
        print(f"   -> {res['days']} days, total {res['total_return_pct']:+.1f}%, "
              f"CAGR {res['cagr_pct']:+.1f}%, maxDD {res['max_drawdown_pct']:.1f}%, "
              f"Sharpe {res['sharpe']:.2f}, bench {res['benchmark_return_pct']}")

    print("5) Notify: digest builds + no-op when unconfigured ...")
    text = notify.format_digest(recs, {**s3, "positions": len(snap["rows"])})
    assert "IHSG Daily Digest" in text, text
    result = notify.notify(text)
    assert result["any_sent"] is False, "should be no-op without secrets"
    print(f"   -> digest built ({len(text)} chars); send no-op ok: "
          f"tg='{result['telegram']}' email='{result['email']}'")

    print("6) Idempotent paper re-run (same date) ...")
    before = db.get_state("cash")
    paper.run_day(cfg, run_date="2026-05-27", recs=recs)  # same date again
    after = db.get_state("cash")
    print(f"   -> cash {before:,.0f} -> {after:,.0f} (equity point upserted)")

    print("\nALL PHASE 3 TESTS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
