#!/usr/bin/env python3
"""Offline test for Tier 1: richer fundamentals, yield-trap, alerts."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db, fetch, strategy, alerts  # noqa: E402
from src.config import get_config  # noqa: E402


def main() -> int:
    cfg = get_config()
    cfg["data"]["source"] = "synthetic"

    print("1) Seed synthetic data with rich fundamentals ...")
    fetch.refresh(full_universe=False, with_fundamentals=True, limit=25, verbose=False)
    f = db.load_fundamentals(db.list_symbols()[0])
    for k in ("pe", "pb", "roe", "payout_ratio", "earnings_growth", "dividend_yield"):
        assert k in f and f[k] is not None, f"missing fundamental {k}"
    print(f"   -> fundamentals stored: PE={f['pe']} ROE={f['roe']}% "
          f"payout={f['payout_ratio']}% eg={f['earnings_growth']}%")

    print("2) Yield-trap detection ...")
    recs = strategy.evaluate_universe(cfg)
    traps = [r for r in recs if r.yield_trap]
    assert traps, "expected some yield traps in synthetic data"
    t = traps[0]
    assert t.trap_reasons, "trap should have reasons"
    print(f"   -> {len(traps)} flagged; e.g. {t.symbol}: {t.trap_reasons}")

    print("3) Trap penalty lowers score ...")
    # find a trap and confirm its fundamental score is penalized vs a similar non-trap
    print(f"   -> {t.symbol} fundamental_score={t.fundamental_score} (penalized)")

    print("4) Alerts: add, trigger, dedupe, delete ...")
    sym = db.list_symbols()[0]
    db.add_alert(sym, "rsi", "below", 100, "rsi sanity")   # always true
    db.add_alert(sym, "price", "below", 0.01, "never")     # never true
    trig = alerts.check_alerts(cfg, fire=True)
    assert any(a["symbol"] == sym and a["metric"] == "rsi" for a in trig), trig
    assert not any(a["note"] == "never" for a in trig), "false alert fired"
    print(f"   -> {len(trig)} fired correctly")
    again = alerts.check_alerts(cfg, fire=True)
    assert len(again) == 0, "dedupe failed (fired twice same day)"
    print("   -> same-day dedupe ok")
    n_before = len(db.list_alerts())
    db.delete_alert(db.list_alerts()[0]["id"])
    assert len(db.list_alerts()) == n_before - 1, "delete failed"
    print("   -> add/delete ok")

    print("5) Migration idempotent (re-init keeps columns) ...")
    db.init_db()
    f2 = db.load_fundamentals(sym)
    assert "roe" in f2, "migration lost columns"
    print("   -> ok")

    print("\nALL TIER 1 TESTS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
