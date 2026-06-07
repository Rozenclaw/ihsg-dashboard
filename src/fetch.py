"""Orchestrates: build universe -> pull history (BATCHED) + fundamentals -> SQLite.

Prices are fetched in batches (one request per chunk of tickers) so the full IDX
universe (~958 names) is feasible — per-symbol downloads would take far too long.
Fundamentals are still per-symbol (Yahoo has no batch .info) and best-effort, and
also backfill each security's display name + sector. Prices are fetched FIRST so
an interrupted/rate-limited fundamentals pass still leaves complete price data.
"""
from __future__ import annotations

import time

from . import db
from .config import get_config
from .datasources import get_source
from .universe import load_full_universe, seed_universe


def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def refresh(full_universe: bool = False, with_fundamentals: bool = True,
            limit: int | None = None, verbose: bool = True,
            batch_size: int = 60, prune_empty: bool = False) -> dict:
    cfg = get_config()
    dcfg = cfg["data"]
    src = get_source(dcfg["source"])
    db.init_db()

    universe = load_full_universe() if full_universe else seed_universe()
    if limit:
        universe = universe[:limit]

    # Register the index + each security (names may be blank; fundamentals fill them).
    index_symbol = dcfg["index_symbol"]
    db.upsert_security(index_symbol, "IDX Composite (IHSG)", "Index", is_index=True)
    for sym, name, sector in universe:
        db.upsert_security(sym, name, sector, is_index=False)

    targets = [index_symbol] + [u[0] for u in universe]
    period, interval = dcfg["history_period"], dcfg["history_interval"]
    pause = dcfg.get("request_pause_sec", 0.0)

    total_rows, ok = 0, 0
    errors: list[str] = []

    # ---- 1) PRICES — batched (the core data; fast even for ~958 names) ----
    done = 0
    for chunk in _chunk(targets, batch_size):
        try:
            frames = src.history_batch(chunk, period, interval)
        except Exception as e:                       # whole-chunk failure
            errors.append(f"batch@{chunk[0]}: {e}")
            frames = {}
        for sym in chunk:
            hist = frames.get(sym)
            try:
                rows = db.save_prices(sym, hist) if hist is not None else 0
                total_rows += rows
                if rows:
                    ok += 1
            except Exception as e:
                errors.append(f"{sym}: {e}")
        done += len(chunk)
        if verbose:
            print(f"[prices {done}/{len(targets)}] {ok} ok, {total_rows} rows")
        time.sleep(pause)

    # ---- 2) FUNDAMENTALS — per-symbol, best-effort; also backfills name/sector ----
    if with_fundamentals:
        fsyms = [u[0] for u in universe]
        fpause = min(pause, 0.3)                      # lighter spacing for .info
        fok = 0
        for i, sym in enumerate(fsyms, 1):
            try:
                fund = src.fundamentals(sym)
                if fund:
                    db.save_fundamentals(sym, fund)
                    db.update_security_meta(sym, fund.get("name"), fund.get("sector"))
                    fok += 1
            except Exception as e:
                errors.append(f"{sym} fund: {e}")
            if verbose and i % 100 == 0:
                print(f"[fundamentals {i}/{len(fsyms)}] {fok} ok")
            time.sleep(fpause)

    if prune_empty:
        pruned = db.prune_securities_without_prices()
        if verbose and pruned:
            print(f"[prune] dropped {pruned} tickers with no price data")

    status = "ok" if not errors else ("partial" if ok else "failed")
    db.log_refresh(src.name, len(targets), total_rows, status, "; ".join(errors[:5]))
    summary = {"source": src.name, "symbols": len(targets), "ok": ok,
               "rows": total_rows, "status": status, "errors": errors}
    if verbose:
        print(f"\nDone: {ok}/{len(targets)} priced, {total_rows} rows, "
              f"status={status}, {len(errors)} errors")
    return summary
