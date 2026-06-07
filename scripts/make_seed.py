#!/usr/bin/env python3
"""Build data/seed.db — a committed market-data snapshot for cloud deploys.

Streamlit Community Cloud has an ephemeral filesystem, so the live DB
(data/ihsg.db, gitignored) is absent on every cold boot. This script copies ONLY
the market-data tables (securities, prices, fundamentals) from the live DB into a
small, committable data/seed.db. The app lays this down on first cloud boot so it
always has data to show — even before (or instead of) a live refresh.

Personal tables (paper trades/positions/equity, real holdings, alerts, signals)
are intentionally EXCLUDED so nothing private ends up in git.

Run before pushing if you want the cloud seed to reflect fresh prices:
    python scripts/make_seed.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db as _db  # noqa: E402
from src.config import PROJECT_ROOT, db_path  # noqa: E402

# Only read-only market data the dashboard renders from.
SEED_TABLES = ["securities", "prices", "fundamentals"]


def main() -> None:
    src_path = db_path()
    dst_path = os.path.join(PROJECT_ROOT, "data", "seed.db")
    if not os.path.exists(src_path):
        sys.exit(f"Live DB not found at {src_path}. Run scripts/refresh_data.py first.")

    if os.path.exists(dst_path):
        os.remove(dst_path)

    src = sqlite3.connect(src_path)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(dst_path)
    try:
        dst.executescript(_db.SCHEMA)        # full app schema (incl. migrated cols)
        total = 0
        for table in SEED_TABLES:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"  {table}: 0 rows (skipped)")
                continue
            cols = rows[0].keys()
            placeholders = ",".join(["?"] * len(cols))
            dst.executemany(
                f"INSERT INTO {table}({','.join(cols)}) VALUES({placeholders})",
                [tuple(r) for r in rows],
            )
            total += len(rows)
            print(f"  {table}: {len(rows):,} rows")
        dst.commit()
    finally:
        src.close()
        dst.close()

    size_mb = os.path.getsize(dst_path) / 1e6
    print(f"\nWrote {dst_path}  ({size_mb:.1f} MB, {total:,} rows total)")


if __name__ == "__main__":
    main()
