#!/usr/bin/env python3
"""Offline end-to-end test for Phase 2 (synthetic data, no network)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db, fetch, strategy  # noqa: E402
from src.config import get_config  # noqa: E402


def main() -> int:
    cfg = get_config()
    cfg["data"]["source"] = "synthetic"

    print("1) Seeding synthetic universe (15 symbols) ...")
    fetch.refresh(full_universe=False, with_fundamentals=True, limit=15, verbose=False)

    print("2) Evaluating single symbol ...")
    syms = db.list_symbols(include_index=False)
    r = strategy.evaluate(syms[0], cfg)
    assert r.action in ("BUY", "HOLD", "SELL", "SKIP"), r
    assert r.composite is None or 0 <= r.composite <= 100, r
    print(f"   -> {r.symbol}: {r.action} composite={r.composite} "
          f"yield={r.div_yield_pct} rsi={r.rsi}")

    print("3) Scoring bounds + sizing sanity ...")
    recs = strategy.evaluate_universe(cfg)
    assert recs, "no recommendations"
    for x in recs:
        if x.fundamental_score is not None:
            assert 0 <= x.fundamental_score <= 100, x
        if x.technical_score is not None:
            assert 0 <= x.technical_score <= 100, x
        if x.action == "BUY":
            assert x.entry and x.target and x.stop, x
            assert x.target > x.entry > x.stop, f"level order wrong: {x}"
            assert x.lots is not None and x.lots >= 0, x
    print(f"   -> {len(recs)} evaluated; sizing/levels consistent for BUYs")

    print("4) Ranking: BUY before SELL/SKIP ...")
    order = {"BUY": 0, "HOLD": 1, "SELL": 2, "SKIP": 3}
    seq = [order.get(r.action, 9) for r in recs]
    assert seq == sorted(seq), "not ranked by action priority"
    print(f"   -> action order ok: {[r.action for r in recs[:6]]}")

    print("5) Persisting signals to DB ...")
    n = db.save_signals("2026-05-29", [r.as_row() for r in recs])
    back = db.load_signals("2026-05-29")
    assert n == len(recs) and len(back) == n, (n, len(back))
    # idempotent re-run
    db.save_signals("2026-05-29", [r.as_row() for r in recs])
    assert len(db.load_signals("2026-05-29")) == n, "not idempotent"
    print(f"   -> stored & reloaded {n} signals; upsert idempotent")

    counts = {}
    for r in recs:
        counts[r.action] = counts.get(r.action, 0) + 1
    print(f"\nAction summary: {counts}")
    print("ALL PHASE 2 TESTS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
