"""Cloud data bootstrap.

Streamlit Community Cloud (and similar hosts) give the app an **ephemeral
filesystem** — the local SQLite DB (gitignored) is absent on every cold boot and
wiped on every restart/redeploy. So on a cloud host we:

  1. **Seed instantly** from the committed ``data/seed.db.gz`` (market data only,
     decompressed in-place), so the dashboard always has the full universe even if
     the live source is unreachable from the host.
  2. **Freshen prices best-effort** via ``fetch.refresh`` — but only when a new IDX
     session is actually due (once a day, after close, never on weekends/holidays;
     see src/market_calendar) and non-fatal if Yahoo rate-limits the cloud IP.

Locally this is a **no-op**: ``start.command`` (or a manual refresh) already owns
the data, and the DB persists on disk, so the app loads instantly as before.
Detection is by the checkout path (Community Cloud mounts the repo under
``/mount/``) or the ``IHSG_CLOUD=1`` / ``IHSG_FORCE_BOOTSTRAP=1`` env override.
"""
from __future__ import annotations

import gzip
import os
import shutil

import streamlit as st

from src import db, market_calendar
from src.config import PROJECT_ROOT, db_path, get_config


def _seed_path() -> str:
    return os.path.join(PROJECT_ROOT, "data", "seed.db.gz")


def _on_cloud() -> bool:
    """True on an ephemeral cloud host where we must self-seed the DB."""
    if os.environ.get("IHSG_FORCE_BOOTSTRAP") == "1" or os.environ.get("IHSG_CLOUD") == "1":
        return True
    # Streamlit Community Cloud checks the repo out under /mount/src/<repo>/...
    return PROJECT_ROOT.startswith("/mount/")


def _has_data() -> bool:
    try:
        return len(db.list_symbols(include_index=False)) > 0
    except Exception:
        return False


def _due_for_refresh() -> bool:
    """Whether a newer IDX session is available than our latest stored bar — the
    once-a-day, after-close, skip-weekends/holidays rule (see src/market_calendar)."""
    idx = (get_config().get("data") or {}).get("index_symbol", "^JKSE")
    return market_calendar.should_refresh(db.latest_price_date(idx))


@st.cache_resource(ttl=21600, show_spinner=False)   # re-check ~4×/day per container
def ensure_data() -> bool:
    """Guarantee the dashboard has data on cloud hosts. Cached as a resource so
    the (potentially slow) check runs at most once per TTL window per container."""
    # 1) Lay down the committed seed if the DB is empty — covers a fresh local
    #    clone AND every cloud cold boot (the cloud disk is ephemeral). Instant
    #    full-universe baseline, decompressed from the gzipped snapshot.
    if not _has_data():
        seed, target = _seed_path(), db_path()      # db_path() also creates data/
        if os.path.exists(seed):
            try:
                with gzip.open(seed, "rb") as f_in, open(target, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            except Exception:
                pass
        try:
            db.init_db()                # ensure schema exists even with no seed file
        except Exception:
            pass

    # 2) Freshen PRICES only — CLOUD ONLY (locally, start.command / the Refresh
    #    button own freshness, so we never slow a local launch). Full-universe price
    #    refresh is a handful of batched requests (feasible on the free tier);
    #    fundamentals stay at seed values (they change slowly). Best effort: on
    #    failure we keep serving the seed snapshot.
    if _on_cloud() and _due_for_refresh():
        try:
            from src import fetch
            with st.spinner("📡 Updating the latest IHSG prices… "
                            "(first load can take a minute)"):
                fetch.refresh(full_universe=True, with_fundamentals=False,
                              verbose=False)
            st.cache_data.clear()       # drop recs/prices cached from stale data
        except Exception:
            pass

    return True
