#!/usr/bin/env python3
"""Build data/seed.db.gz — a committed market-data snapshot for cloud deploys.

Streamlit Community Cloud has an ephemeral filesystem, so the live DB
(data/ihsg.db, gitignored) is absent on every cold boot. This copies the
read-only market tables (securities, prices, fundamentals, refresh_log) from the
live DB into a small SQLite file and GZIPS it — the full ~950-stock × 5y dataset
is ~130 MB raw (over GitHub's 100 MB limit) but compresses to a committable size.
The app decompresses it on first cloud boot (see app/ui/bootstrap.py).

Personal tables (paper trades/positions/equity, holdings, alerts, signals) are
intentionally EXCLUDED so nothing private ends up in git.

Run before pushing if you want a fresher cloud snapshot:
    python scripts/make_seed.py            # full history
    python scripts/make_seed.py --years 3  # trim prices to last 3y (smaller file)
"""
import argparse
import datetime as dt
import gzip
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db as _db  # noqa: E402
from src.config import PROJECT_ROOT, db_path  # noqa: E402

# Read-only market data + the refresh log (so the cloud knows the snapshot's age).
SEED_TABLES = ["securities", "prices", "fundamentals", "refresh_log"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=None,
                    help="trim price history to the last N years (smaller file)")
    args = ap.parse_args()

    src_path = db_path()
    tmp_path = os.path.join(PROJECT_ROOT, "data", "seed.db")
    gz_path = tmp_path + ".gz"
    if not os.path.exists(src_path):
        sys.exit(f"Live DB not found at {src_path}. Run scripts/refresh_data.py first.")

    cutoff = None
    if args.years:
        cutoff = (dt.date.today() - dt.timedelta(days=365 * args.years)).isoformat()

    for p in (tmp_path, gz_path):
        if os.path.exists(p):
            os.remove(p)

    src = sqlite3.connect(src_path)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(tmp_path)
    try:
        dst.executescript(_db.SCHEMA)
        total = 0
        for table in SEED_TABLES:
            where = ""
            if table == "prices" and cutoff:
                where = f" WHERE date >= '{cutoff}'"
            rows = src.execute(f"SELECT * FROM {table}{where}").fetchall()
            if not rows:
                print(f"  {table}: 0 rows")
                continue
            cols = rows[0].keys()
            ph = ",".join(["?"] * len(cols))
            dst.executemany(
                f"INSERT INTO {table}({','.join(cols)}) VALUES({ph})",
                [tuple(r) for r in rows])
            total += len(rows)
            print(f"  {table}: {len(rows):,} rows")
        dst.commit()
    finally:
        src.close()
        dst.close()

    # gzip the snapshot, then drop the uncompressed copy.
    with open(tmp_path, "rb") as f_in, gzip.open(gz_path, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)
    raw_mb = os.path.getsize(tmp_path) / 1e6
    gz_mb = os.path.getsize(gz_path) / 1e6
    os.remove(tmp_path)

    print(f"\nWrote {gz_path}")
    print(f"  {total:,} rows · raw {raw_mb:.0f} MB -> gzip {gz_mb:.0f} MB")
    if gz_mb > 95:
        print("  ⚠️  Over ~95 MB — re-run with e.g. --years 3 to stay under "
              "GitHub's 100 MB file limit.")


if __name__ == "__main__":
    main()
