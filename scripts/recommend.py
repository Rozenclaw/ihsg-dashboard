#!/usr/bin/env python3
"""CLI: run the Phase 2 strategy across the universe and store daily signals.

Examples:
  python scripts/recommend.py                 # evaluate all stored symbols
  python scripts/recommend.py --top 15        # print top 15 BUY/HOLD
  python scripts/recommend.py --date 2026-05-29
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from src import db, strategy  # noqa: E402
from src.config import get_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20, help="rows to print")
    ap.add_argument("--date", help="run date label (default: today)")
    ap.add_argument("--no-store", action="store_true", help="don't write to DB")
    args = ap.parse_args()

    cfg = get_config()
    db.init_db()
    run_date = args.date or pd.Timestamp.today().strftime("%Y-%m-%d")

    recs = strategy.evaluate_universe(cfg)
    rows = [r.as_row() for r in recs]
    if not args.no_store:
        n = db.save_signals(run_date, rows)
        print(f"Stored {n} signals for {run_date}\n")

    df = pd.DataFrame(rows)
    if df.empty:
        print("No data. Run scripts/refresh_data.py first.")
        return
    show = df[df["action"].isin(["BUY", "HOLD", "SELL"])].head(args.top)
    cols = ["symbol", "action", "composite", "div_yield_pct", "rsi", "trend",
            "entry", "target", "stop", "lots", "rationale"]
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.max_colwidth", 50):
        print(show[cols].to_string(index=False))

    counts = df["action"].value_counts().to_dict()
    print(f"\nSummary: {counts}")


if __name__ == "__main__":
    main()
