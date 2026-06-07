#!/usr/bin/env python3
"""Build data/universe.csv — the FULL IDX (Bursa Efek Indonesia) ticker list.

Yahoo Finance can fetch any ".JK" ticker, but the app only pulls the symbols it
is told about. This script enumerates (nearly) every IDX-listed stock from a free
public source so the dashboard can cover the whole market, not just the curated
liquid subset in src/universe.py.

Source: the community dataset `wildangunawan/Dataset-Saham-IDX`, which keeps one
price CSV per ticker under Saham/Semua/ — its directory listing IS the ticker
list (~958 symbols). Free, no key. Re-run anytime to refresh the list; newly
listed stocks appear once that dataset (or any source you point this at) updates.

Curated names/sectors from src/universe.SEED_UNIVERSE are merged in so the most
common names keep good labels; the rest get their name/sector filled from Yahoo
during the data refresh. Output columns: symbol,name,sector (symbol incl. .JK).

Run:  python scripts/fetch_idx_universe.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import PROJECT_ROOT  # noqa: E402
from src.universe import SEED_UNIVERSE  # noqa: E402

CONTENTS_API = ("https://api.github.com/repos/wildangunawan/Dataset-Saham-IDX/"
                "contents/Saham/Semua?per_page=1000")
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}


def fetch_tickers() -> list[str]:
    req = urllib.request.Request(CONTENTS_API, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.load(r)
    if isinstance(data, dict):
        raise SystemExit(f"GitHub API error: {data.get('message')}")
    tickers = sorted(x["name"][:-4] for x in data
                     if x.get("name", "").endswith(".csv"))
    return tickers


def main() -> None:
    bare = fetch_tickers()
    # Curated labels for the names we already know (keep ".JK" form).
    curated = {sym: (name, sector) for sym, name, sector in SEED_UNIVERSE}

    rows = []
    for t in bare:
        sym = t if t.endswith(".JK") else f"{t}.JK"
        name, sector = curated.get(sym, ("", ""))
        rows.append((sym, name, sector))

    # Make sure every curated name is present even if missing from the source.
    have = {r[0] for r in rows}
    for sym, name, sector in SEED_UNIVERSE:
        if sym not in have:
            rows.append((sym, name, sector))
    rows.sort(key=lambda r: r[0])

    out = os.path.join(PROJECT_ROOT, "data", "universe.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "name", "sector"])
        w.writerows(rows)

    named = sum(1 for r in rows if r[1])
    print(f"Wrote {out}")
    print(f"  {len(rows)} IDX tickers ({named} with curated names; "
          f"the rest fill name/sector from Yahoo on refresh)")


if __name__ == "__main__":
    main()
