#!/usr/bin/env python3
"""CLI: refresh IHSG data into SQLite.

Examples:
  python scripts/refresh_data.py                 # seed universe, live source from config
  python scripts/refresh_data.py --full          # full universe from data/universe.csv
  python scripts/refresh_data.py --source synthetic   # offline test data
  python scripts/refresh_data.py --limit 5       # quick partial run
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import fetch  # noqa: E402
from src.config import get_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="use full universe CSV")
    ap.add_argument("--source", help="override data source (yfinance|synthetic)")
    ap.add_argument("--limit", type=int, help="limit number of symbols")
    ap.add_argument("--no-fundamentals", action="store_true")
    args = ap.parse_args()

    if args.source:
        # override in-memory config
        cfg = get_config()
        cfg["data"]["source"] = args.source

    fetch.refresh(full_universe=args.full,
                  with_fundamentals=not args.no_fundamentals,
                  limit=args.limit, verbose=True)


if __name__ == "__main__":
    main()
