#!/usr/bin/env python3
"""CLI: refresh IHSG data into SQLite.

Examples:
  python scripts/refresh_data.py                 # FULL IDX universe (prices + fundamentals)
  python scripts/refresh_data.py --prices-only   # fast daily refresh (batched prices, all names)
  python scripts/refresh_data.py --seed          # only the curated ~75-name list
  python scripts/refresh_data.py --source synthetic   # offline test data
  python scripts/refresh_data.py --limit 20      # quick partial run
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db, fetch, market_calendar  # noqa: E402
from src.config import get_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true",
                    help="use only the curated ~75-name seed list (small/fast) "
                         "instead of the full IDX universe (data/universe.csv)")
    ap.add_argument("--prices-only", action="store_true",
                    help="skip the slow per-symbol fundamentals pass (fast daily "
                         "refresh: batched prices for the whole universe)")
    ap.add_argument("--if-due", action="store_true",
                    help="only refresh if a new IDX session is available — once a "
                         "day, after the close, never on weekends/holidays")
    ap.add_argument("--source", help="override data source (yfinance|synthetic)")
    ap.add_argument("--limit", type=int, help="limit number of symbols")
    ap.add_argument("--no-fundamentals", action="store_true",
                    help="alias of --prices-only")
    args = ap.parse_args()

    if args.source:
        # override in-memory config
        cfg = get_config()
        cfg["data"]["source"] = args.source

    if args.if_due:
        idx = get_config()["data"]["index_symbol"]
        latest = db.latest_price_date(idx)
        if not market_calendar.should_refresh(latest):
            print(f"[skip] No new IDX session due — "
                  f"{market_calendar.skip_reason(latest)}. (Use --refresh to force.)")
            return

    full = not args.seed
    fetch.refresh(full_universe=full,
                  with_fundamentals=not (args.prices_only or args.no_fundamentals),
                  limit=args.limit, prune_empty=full, verbose=True)


if __name__ == "__main__":
    main()
