"""Dividend calendar helper (Tier 2).

Computes cum-date / ex-date info from the stored `ex_dividend_date` fundamental
(sourced free from Yahoo). On IDX the **cum-date** (last day to buy and still
receive the dividend) is the trading day *before* the ex-date.

For a stacking strategy, "days to cum-date" tells you how long you have to
accumulate before you'd miss this dividend cycle. Gracefully returns None when
no ex-date is available.

NOT financial advice.
"""
from __future__ import annotations

import pandas as pd


def cum_date(ex_date: str | None) -> str | None:
    """Cum-date = one business day before the ex-date."""
    if not ex_date:
        return None
    try:
        ex = pd.Timestamp(ex_date)
    except Exception:
        return None
    return (ex - pd.tseries.offsets.BDay(1)).strftime("%Y-%m-%d")


def days_to(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        d = pd.Timestamp(date_str).normalize()
    except Exception:
        return None
    return int((d - pd.Timestamp.today().normalize()).days)


def info(ex_date: str | None) -> dict:
    """Return {ex_date, cum_date, days_to_cum, status}."""
    cum = cum_date(ex_date)
    dtc = days_to(cum)
    if ex_date is None:
        status = "no upcoming ex-date"
    elif dtc is None:
        status = "—"
    elif dtc < 0:
        status = "passed"
    elif dtc == 0:
        status = "cum-date is TODAY — last day to buy"
    elif dtc <= 5:
        status = f"{dtc}d to cum-date — buy soon to qualify"
    else:
        status = f"{dtc}d to cum-date"
    return {"ex_date": ex_date, "cum_date": cum, "days_to_cum": dtc, "status": status}


def label(ex_date: str | None, lang: str = "EN") -> str:
    inf = info(ex_date)
    dtc = inf["days_to_cum"]
    if ex_date is None or dtc is None:
        return "—"
    if lang == "ID":
        if dtc < 0:
            return f"cum-date sudah lewat (ex {inf['ex_date']})"
        if dtc == 0:
            return f"🔔 cum-date HARI INI — terakhir beli untuk dapat dividen"
        if dtc <= 5:
            return f"⏰ {dtc} hari ke cum-date ({inf['cum_date']}) — beli sebelum ini"
        return f"{dtc} hari ke cum-date ({inf['cum_date']})"
    if dtc < 0:
        return f"cum-date passed (ex {inf['ex_date']})"
    if dtc == 0:
        return "🔔 cum-date is TODAY — last day to buy for the dividend"
    if dtc <= 5:
        return f"⏰ {dtc}d to cum-date ({inf['cum_date']}) — buy before this to qualify"
    return f"{dtc}d to cum-date ({inf['cum_date']})"
