"""Orchestrates: seed universe -> pull history + fundamentals -> store in SQLite."""
from __future__ import annotations

import time

from . import db
from .config import get_config
from .datasources import get_source
from .universe import load_full_universe, seed_universe


def refresh(full_universe: bool = False, with_fundamentals: bool = True,
            limit: int | None = None, verbose: bool = True) -> dict:
    cfg = get_config()
    dcfg = cfg["data"]
    src = get_source(dcfg["source"])
    db.init_db()

    universe = load_full_universe() if full_universe else seed_universe()
    if limit:
        universe = universe[:limit]

    # Register the index + each security.
    index_symbol = dcfg["index_symbol"]
    db.upsert_security(index_symbol, "IDX Composite (IHSG)", "Index", is_index=True)
    for sym, name, sector in universe:
        db.upsert_security(sym, name, sector, is_index=False)

    targets = [index_symbol] + [u[0] for u in universe]
    total_rows = 0
    ok = 0
    errors: list[str] = []

    for i, sym in enumerate(targets, 1):
        try:
            hist = src.history(sym, dcfg["history_period"], dcfg["history_interval"])
            rows = db.save_prices(sym, hist)
            total_rows += rows
            if with_fundamentals and sym != index_symbol:
                fund = src.fundamentals(sym)
                if fund:
                    db.save_fundamentals(sym, fund)
            ok += 1
            if verbose:
                print(f"[{i}/{len(targets)}] {sym}: {rows} rows")
        except Exception as e:  # keep going on a single-symbol failure
            errors.append(f"{sym}: {e}")
            if verbose:
                print(f"[{i}/{len(targets)}] {sym}: ERROR {e}")
        time.sleep(dcfg.get("request_pause_sec", 0.0))

    status = "ok" if not errors else ("partial" if ok else "failed")
    msg = "; ".join(errors[:5])
    db.log_refresh(src.name, len(targets), total_rows, status, msg)
    summary = {"source": src.name, "symbols": len(targets), "ok": ok,
               "rows": total_rows, "status": status, "errors": errors}
    if verbose:
        print(f"\nDone: {ok}/{len(targets)} symbols, {total_rows} rows, status={status}")
    return summary
