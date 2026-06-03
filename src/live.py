"""iTick realtime quote overlay (free tier).

Fetches near-realtime IDX quotes via iTick's REST endpoint. This is separate
from the EOD data layer (yfinance -> SQLite): it's a thin, live-on-demand
overlay used only by the dashboard's "Live" panel. No storage, no caching here
beyond what the dashboard applies.

API: GET https://api.itick.org/stock/quote?region=ID&code=BBRI
Header: token: <YOUR_KEY>
iTick uses BARE tickers (no .JK) and region=ID.

Get a free key at https://itick.org and set it via either:
  - environment variable:  export ITICK_TOKEN="your_key"
  - Streamlit secrets:     .streamlit/secrets.toml  ->  ITICK_TOKEN = "your_key"
"""
from __future__ import annotations

import os
import time
from typing import Optional

import requests

# iTick assigns each account a specific access host (shown in the dashboard as
# "API ACCESS ADDRESS", e.g. api0.itick.org). Calling the generic api.itick.org
# returns {"message":"Invalid API key in request"}. Override via env ITICK_HOST
# or config live.host if your dashboard shows a different host.
DEFAULT_HOST = "api0.itick.org"
REGION = "ID"
_TIMEOUT = 6
_MAX_RETRIES = 3          # attempts per symbol on 429 / transient errors
_BACKOFF_BASE = 0.8       # seconds; doubles each retry (0.8, 1.6, ...)


def get_host(explicit: Optional[str] = None) -> str:
    """Resolve the iTick access host: arg > env > Streamlit secrets > default."""
    if explicit:
        h = explicit
    else:
        h = os.environ.get("ITICK_HOST")
        if not h:
            try:
                import streamlit as st  # noqa
                if "ITICK_HOST" in st.secrets:
                    h = st.secrets["ITICK_HOST"]
            except Exception:
                h = None
        h = h or DEFAULT_HOST
    return h.replace("https://", "").replace("http://", "").strip("/ ")


def _api_url(host: Optional[str] = None) -> str:
    return f"https://{get_host(host)}/stock/quote"


def get_token(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve the iTick API token from arg > env > Streamlit secrets."""
    if explicit:
        return explicit
    tok = os.environ.get("ITICK_TOKEN")
    if tok:
        return tok
    # Optional: Streamlit secrets (only if streamlit is importable & configured)
    try:
        import streamlit as st  # noqa
        if "ITICK_TOKEN" in st.secrets:
            return st.secrets["ITICK_TOKEN"]
    except Exception:
        pass
    return None


def to_itick_code(symbol: str) -> str:
    """'BBRI.JK' -> 'BBRI'  (iTick uses bare IDX codes)."""
    return symbol.upper().replace(".JK", "").strip()


def fetch_quote(symbol: str, token: Optional[str] = None,
                session: Optional[requests.Session] = None,
                host: Optional[str] = None) -> dict:
    """Fetch one live quote. Returns a normalized dict:
       {symbol, last, open, high, low, volume, ts, ok, error}
    """
    tok = get_token(token)
    out = {"symbol": symbol, "last": None, "open": None, "high": None,
           "low": None, "volume": None, "ts": None, "ok": False, "error": None}
    if not tok:
        out["error"] = "no_token"
        return out

    code = to_itick_code(symbol)
    headers = {"token": tok, "accept": "application/json"}
    params = {"region": REGION, "code": code}
    sess = session or requests
    url = _api_url(host)
    # Retry with exponential backoff on rate-limit (429) / transient errors.
    payload = None
    for attempt in range(_MAX_RETRIES):
        try:
            r = sess.get(url, headers=headers, params=params, timeout=_TIMEOUT)
            if r.status_code == 429:
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_BACKOFF_BASE * (2 ** attempt))
                    continue
                out["error"] = "rate_limited (429) — slow down poll/watchlist"
                return out
            r.raise_for_status()
            payload = r.json()
            break
        except Exception as e:  # network / auth / parse
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE * (2 ** attempt))
                continue
            out["error"] = f"{type(e).__name__}: {e}"
            return out
    if payload is None:
        out["error"] = "no_response"
        return out

    # Gateway-level rejection (wrong host / bad key) uses "message"; iTick app
    # errors use code/msg (E001 not found, E002 auth failed, E003 quota).
    if "message" in payload and "data" not in payload:
        out["error"] = payload["message"]
        return out
    if payload.get("code") not in (0, "0", None):
        out["error"] = payload.get("msg") or f"api_code={payload.get('code')}"
        return out

    d = payload.get("data") or {}
    if isinstance(d, list):  # some responses wrap a single item in a list
        d = d[0] if d else {}
    out.update({
        "last": _num(d.get("ld") if d.get("ld") is not None else d.get("p")),
        "open": _num(d.get("o")),
        "high": _num(d.get("h")),
        "low": _num(d.get("l")),
        "volume": _num(d.get("v")),
        "ts": d.get("t"),
        "ok": d.get("ld") is not None or d.get("p") is not None,
    })
    return out


def fetch_quotes(symbols: list[str], token: Optional[str] = None,
                 pause: float = 1.1) -> dict[str, dict]:
    """Fetch live quotes for several symbols (polite sequential calls).

    Free tier is rate-limited (~1 request/second). We pace calls ~1.1s apart
    and each call retries with backoff on 429. Keep watchlists small (<= ~15)
    and the poll interval >= 60s.
    """
    tok = get_token(token)
    results: dict[str, dict] = {}
    sess = requests.Session()
    for i, sym in enumerate(symbols):
        results[sym] = fetch_quote(sym, token=tok, session=sess)
        if pause and i < len(symbols) - 1:
            time.sleep(pause)
    return results


def _num(v):
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None
