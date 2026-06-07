"""Download a logo for every stock into assets/logos/{TICKER}.png.

Source: the company website from yfinance .info -> that domain's favicon via
Google's favicon service (free, no key, reliable). Real favicons are kept;
Google's generic "globe" fallback (returned for domains with no favicon) is
detected by hashing a known-missing domain's response and skipped, so the app
falls back to a clean gradient monogram for those instead of a generic globe.

Run once (logos rarely change):  python scripts/fetch_logos.py
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "ihsg.db")
LOGODIR = os.path.join(ROOT, "assets", "logos")
SZ = 128
PAUSE = 0.25


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    d = url.split("//")[-1].split("/")[0].strip().lower()
    return d[4:] if d.startswith("www.") else d


def favicon(domain: str) -> requests.Response:
    return requests.get(
        f"https://www.google.com/s2/favicons?domain={domain}&sz={SZ}", timeout=12)


def main() -> int:
    os.makedirs(LOGODIR, exist_ok=True)
    names = {r[0]: r[1] for r in sqlite3.connect(DB).execute(
        "SELECT symbol, name FROM securities WHERE is_index=0")}
    if not names:
        print("no securities in DB", file=sys.stderr)
        return 1

    import yfinance as yf

    # Fingerprint Google's generic "no favicon" globe so we can skip it.
    default_hash = None
    try:
        default_hash = hashlib.md5(
            favicon("no-such-domain-xyz-12345.invalid").content).hexdigest()
    except Exception:
        pass

    ok = mono = 0
    for i, (sym, name) in enumerate(sorted(names.items()), 1):
        tk = sym.replace(".JK", "")
        out = os.path.join(LOGODIR, f"{tk}.png")
        try:
            site = yf.Ticker(sym).info.get("website")
            dom = domain_of(site)
            if not dom:
                mono += 1
                print(f"[{i}/{len(names)}] {tk}: no website -> monogram")
                continue
            r = favicon(dom)
            h = hashlib.md5(r.content).hexdigest()
            good = (r.status_code == 200
                    and r.headers.get("content-type", "").startswith("image")
                    and len(r.content) > 500
                    and h != default_hash)
            if good:
                with open(out, "wb") as f:
                    f.write(r.content)
                ok += 1
                print(f"[{i}/{len(names)}] {tk}: {dom} ({len(r.content)}B) OK")
            else:
                mono += 1
                print(f"[{i}/{len(names)}] {tk}: {dom} no favicon -> monogram")
        except Exception as e:
            mono += 1
            print(f"[{i}/{len(names)}] {tk}: ERROR {type(e).__name__} -> monogram")
        time.sleep(PAUSE)

    print(f"\nDONE: {ok} real logos saved, {mono} will use a monogram fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
