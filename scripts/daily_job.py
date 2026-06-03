#!/usr/bin/env python3
"""Phase 3 daily job — the hands-off automation entry point.

Runs the full pipeline once:
  1. refresh data from Yahoo (EOD)
  2. evaluate strategy + store dated signals
  3. advance the paper portfolio one day
  4. send a digest (Telegram/email; no-op if unconfigured)

Designed to be run by cron / GitHub Actions after IDX close (~09:30 UTC).
Skips silently on weekends unless --force is passed.

Usage:
  python scripts/daily_job.py
  python scripts/daily_job.py --no-refresh        # use existing data
  python scripts/daily_job.py --source synthetic  # offline test
  python scripts/daily_job.py --force             # run even on weekend
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from src import db, fetch, strategy, paper, notify, alerts  # noqa: E402
from src.config import get_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-refresh", action="store_true")
    ap.add_argument("--source", help="override data source")
    ap.add_argument("--force", action="store_true", help="run on weekends too")
    ap.add_argument("--no-notify", action="store_true")
    args = ap.parse_args()

    cfg = get_config()
    if args.source:
        cfg["data"]["source"] = args.source

    today = pd.Timestamp.today()
    if today.weekday() >= 5 and not args.force:
        print(f"[daily_job] {today.date()} is a weekend — IDX closed. Skipping. "
              "(use --force to override)")
        return

    run_date = today.strftime("%Y-%m-%d")
    print(f"[daily_job] run_date={run_date} source={cfg['data']['source']}")

    db.init_db()

    if not args.no_refresh:
        print("[1/4] Refreshing data …")
        summary = fetch.refresh(full_universe=False, with_fundamentals=True, verbose=False)
        print(f"      {summary['ok']}/{summary['symbols']} symbols, "
              f"{summary['rows']} rows, status={summary['status']}")
    else:
        print("[1/4] Skipping refresh (--no-refresh)")

    print("[2/4] Evaluating strategy …")
    recs = strategy.evaluate_universe(cfg)
    db.save_signals(run_date, [r.as_row() for r in recs])
    counts = {}
    for r in recs:
        counts[r.action] = counts.get(r.action, 0) + 1
    print(f"      signals: {counts}")

    print("[3/4] Advancing paper portfolio …")
    psum = paper.run_day(cfg, run_date=run_date, recs=recs)
    print(f"      equity {psum['equity']:,.0f} IDR ({psum['total_return_pct']:+.1f}%), "
          f"{psum['positions']} positions; actions: {psum['actions'] or 'none'}")

    print("[4/4] Checking alerts + sending digest …")
    triggered = alerts.check_alerts(cfg, fire=True)
    if triggered:
        print(f"      {len(triggered)} alert(s) triggered")
    if args.no_notify:
        print("      digest skipped (--no-notify)")
    else:
        text = notify.format_digest(recs, psum)
        alert_text = alerts.format_digest(triggered)
        if alert_text:
            text = alert_text + "\n\n" + text
        result = notify.notify(text)
        print(f"      telegram: {result['telegram']} | email: {result['email']}")
        if not result["any_sent"]:
            print("      (configure TELEGRAM_* or SMTP_* to receive digests)")

    print("[daily_job] done.")


if __name__ == "__main__":
    main()
