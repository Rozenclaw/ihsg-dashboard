"""Cloud data bootstrap.

Streamlit Community Cloud (and similar hosts) give the app an **ephemeral
filesystem** — the local SQLite DB (gitignored) is absent on every cold boot and
wiped on every restart/redeploy. So on a cloud host we:

  1. **Seed instantly** from the committed ``data/seed.db`` (market data only),
     so the dashboard always has something to show even if the live data source
     is unreachable from the host.
  2. **Freshen best-effort** to today's prices via ``fetch.refresh`` — non-fatal
     if Yahoo rate-limits the shared cloud IP (we keep serving the seed).

Locally this is a **no-op**: ``start.command`` (or a manual refresh) already owns
the data, and the DB persists on disk, so the app loads instantly as before.
Detection is by the checkout path (Community Cloud mounts the repo under
``/mount/``) or the ``IHSG_CLOUD=1`` / ``IHSG_FORCE_BOOTSTRAP=1`` env override.
"""
from __future__ import annotations

import datetime as _dt
import os
import shutil

import streamlit as st

from src import db
from src.config import PROJECT_ROOT, db_path


def _today_utc() -> str:
    return _dt.datetime.utcnow().strftime("%Y-%m-%d")


def _seed_path() -> str:
    return os.path.join(PROJECT_ROOT, "data", "seed.db")


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


def _is_stale() -> bool:
    """True if we have never refreshed, or the last refresh predates today (UTC)."""
    last = db.last_refresh()
    if not last or not last.get("run_at"):
        return True
    return str(last["run_at"])[:10] < _today_utc()


@st.cache_resource(ttl=21600, show_spinner=False)   # re-check ~4×/day per container
def ensure_data() -> bool:
    """Guarantee the dashboard has data on cloud hosts. Cached as a resource so
    the (potentially slow) check runs at most once per TTL window per container."""
    if not _on_cloud():
        return True                     # local: leave data to start.command / manual refresh

    # 1) Lay down the committed seed if the DB is empty (instant baseline).
    if not _has_data():
        seed, target = _seed_path(), db_path()      # db_path() also creates data/
        if os.path.exists(seed) and os.path.abspath(seed) != os.path.abspath(target):
            try:
                shutil.copyfile(seed, target)
            except Exception:
                pass
        try:
            db.init_db()                # ensure schema exists even with no seed file
        except Exception:
            pass

    # 2) Freshen to today's data — best effort; keep serving seed/stale on failure.
    if _is_stale():
        try:
            from src import fetch
            with st.spinner("📡 Fetching the latest IHSG market data… "
                            "(first load can take a minute)"):
                fetch.refresh(verbose=False)
            st.cache_data.clear()       # drop recs/prices cached from stale data
        except Exception:
            pass

    return True
