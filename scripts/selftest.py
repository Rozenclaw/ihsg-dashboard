#!/usr/bin/env python3
"""Offline end-to-end smoke test (no network).

Forces the synthetic data source, runs a small refresh, then verifies the
DB -> indicators -> snapshot pipeline. Exits non-zero on failure.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db, fetch, indicators  # noqa: E402
from src.config import get_config  # noqa: E402


def main() -> int:
    cfg = get_config()
    cfg["data"]["source"] = "synthetic"
    cfg["data"]["history_period"] = "2y"

    print("1) Refreshing 6 symbols with synthetic data ...")
    summary = fetch.refresh(full_universe=False, with_fundamentals=True,
                            limit=6, verbose=False)
    assert summary["status"] in ("ok", "partial"), summary
    assert summary["rows"] > 0, "no rows written"
    print(f"   -> {summary['ok']} symbols, {summary['rows']} rows, status={summary['status']}")

    print("2) Checking index + securities ...")
    syms = db.list_symbols(include_index=False)
    assert syms, "no securities stored"
    print(f"   -> {len(syms)} securities: {syms[:5]}...")

    print("3) Indicators on IHSG ...")
    idx = get_config()["data"]["index_symbol"]
    df = indicators.enrich(db.load_prices(idx), cfg)
    assert not df.empty and "rsi" in df.columns, "indicator enrich failed"
    snap = indicators.snapshot(df, cfg)
    assert snap.get("close") is not None, "snapshot missing close"
    print(f"   -> IHSG close={snap['close']:.2f} rsi={snap['rsi']:.1f} trend={snap['trend']}")

    print("4) Fundamentals + yield calc on first stock ...")
    s0 = syms[0]
    f = db.load_fundamentals(s0)
    assert f, "no fundamentals"
    dy = (f["last_dividend"] / f["price"]) * 100
    print(f"   -> {s0} price={f['price']:.0f} div={f['last_dividend']:.0f} yield={dy:.2f}%")

    print("\nALL CHECKS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
