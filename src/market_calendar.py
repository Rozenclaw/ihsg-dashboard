"""IDX trading-calendar rules for deciding WHEN to refresh market data.

Rule (per the dashboard owner): update at most ONCE per trading day, AFTER the IDX
session has closed and Yahoo has posted the end-of-day bar — so the data is ready
for the next day's decisions. NEVER refresh on weekends or Indonesian market
holidays.

Notes:
- Indonesia uses a single timezone, WIB = UTC+7 (no DST), so we just shift UTC.
- IDX trades Mon-Fri ~09:00-16:00 WIB; Yahoo posts the daily close within ~1h, so
  we treat a session's bar as "available" from 17:00 WIB.
- FIXED_HOLIDAYS are recurring national holidays (no yearly maintenance). The
  lunar/variable holidays (Idul Fitri, Imlek, Nyepi, Waisak, Isra Miraj, Idul
  Adha, etc.) shift each year — add IDX's official dates to MOVABLE_HOLIDAYS.
  Leaving one out is SAFE (Yahoo just returns no new bar -> a harmless no-op);
  a WRONG date would skip a real session, so only add confirmed dates.
"""
from __future__ import annotations

import datetime as dt

WIB = dt.timedelta(hours=7)
SESSION_AVAILABLE_HOUR = 17        # WIB hour after which the day's close is on Yahoo

# Recurring fixed-date national holidays the IDX is closed for. (month, day).
FIXED_HOLIDAYS = {
    (1, 1),     # New Year's Day
    (5, 1),     # Labour Day
    (6, 1),     # Pancasila Day
    (8, 17),    # Independence Day
    (12, 25),   # Christmas Day
}

# Variable-date holidays — ISO "YYYY-MM-DD". Update yearly from the official IDX
# holiday schedule (https://www.idx.co.id). Only add CONFIRMED dates.
MOVABLE_HOLIDAYS: set[str] = set()


def now_jkt(now_utc: dt.datetime | None = None) -> dt.datetime:
    return (now_utc or dt.datetime.utcnow()) + WIB


def is_trading_day(d: dt.date) -> bool:
    if d.weekday() >= 5:                       # Saturday / Sunday
        return False
    if (d.month, d.day) in FIXED_HOLIDAYS:
        return False
    if d.isoformat() in MOVABLE_HOLIDAYS:
        return False
    return True


def _prev_trading_day(d: dt.date) -> dt.date:
    d -= dt.timedelta(days=1)
    while not is_trading_day(d):
        d -= dt.timedelta(days=1)
    return d


def last_session(now_utc: dt.datetime | None = None) -> dt.date:
    """The most recent IDX session whose EOD bar should be available on Yahoo."""
    j = now_jkt(now_utc)
    if is_trading_day(j.date()) and j.hour >= SESSION_AVAILABLE_HOUR:
        return j.date()
    return _prev_trading_day(j.date())


def should_refresh(latest_bar_iso: str | None,
                   now_utc: dt.datetime | None = None) -> bool:
    """True iff a newer completed session exists than the latest bar we have.

    - Weekend / holiday: last_session is the prior session, so once it's stored
      this returns False (no refresh).
    - Before ~17:00 WIB: last_session is the previous day; once stored, waits.
    - After close on a trading day: True until today's bar is stored, then False
      (giving exactly one refresh per trading day)."""
    target = last_session(now_utc)
    if not latest_bar_iso:
        return True
    try:
        latest = dt.date.fromisoformat(str(latest_bar_iso)[:10])
    except Exception:
        return True
    return latest < target


def skip_reason(latest_bar_iso: str | None,
                now_utc: dt.datetime | None = None) -> str:
    """Human-readable reason a refresh is being skipped (for logs/CLI)."""
    j = now_jkt(now_utc)
    if not is_trading_day(j.date()):
        return "weekend/holiday (IDX closed)"
    if j.hour < SESSION_AVAILABLE_HOUR:
        return f"before ~{SESSION_AVAILABLE_HOUR}:00 WIB (today's close not posted yet)"
    return f"already up to date with the {last_session(now_utc)} session"
