"""SQLite storage layer: schema + read/write helpers."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterable

import pandas as pd

from .config import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    symbol        TEXT PRIMARY KEY,
    name          TEXT,
    sector        TEXT,
    is_index      INTEGER DEFAULT 0,
    active        INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS prices (
    symbol  TEXT NOT NULL,
    date    TEXT NOT NULL,           -- ISO yyyy-mm-dd
    open    REAL,
    high    REAL,
    low     REAL,
    close   REAL,
    volume  REAL,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_prices_symbol ON prices(symbol);

CREATE TABLE IF NOT EXISTS fundamentals (
    symbol           TEXT PRIMARY KEY,
    price            REAL,
    market_cap       REAL,
    beta             REAL,
    last_dividend    REAL,
    range_52w        TEXT,
    sector           TEXT,
    industry         TEXT,
    pe               REAL,
    pb               REAL,
    roe              REAL,
    debt_to_equity   REAL,
    payout_ratio     REAL,
    earnings_growth  REAL,
    dividend_yield   REAL,
    ex_dividend_date TEXT,
    updated_at       TEXT
);

CREATE TABLE IF NOT EXISTS refresh_log (
    run_at      TEXT,
    source      TEXT,
    symbols     INTEGER,
    rows        INTEGER,
    status      TEXT,
    message     TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    run_date          TEXT NOT NULL,
    symbol            TEXT NOT NULL,
    action            TEXT,
    composite         REAL,
    fundamental_score REAL,
    technical_score   REAL,
    close             REAL,
    div_yield_pct     REAL,
    rsi               REAL,
    trend             TEXT,
    range_pos_pct     REAL,
    entry             REAL,
    target            REAL,
    stop              REAL,
    lots              INTEGER,
    est_cost_idr      REAL,
    rationale         TEXT,
    PRIMARY KEY (run_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(run_date);

CREATE TABLE IF NOT EXISTS paper_positions (
    symbol      TEXT PRIMARY KEY,
    lots        INTEGER,
    avg_price   REAL,
    opened_date TEXT,
    target      REAL,
    stop        REAL
);

CREATE TABLE IF NOT EXISTS paper_trades (
    trade_date  TEXT,
    symbol      TEXT,
    side        TEXT,            -- BUY | SELL
    lots        INTEGER,
    price       REAL,
    value       REAL,
    reason      TEXT
);

CREATE TABLE IF NOT EXISTS paper_state (
    key         TEXT PRIMARY KEY,
    value       REAL
);

CREATE TABLE IF NOT EXISTS paper_equity (
    date        TEXT PRIMARY KEY,
    cash        REAL,
    holdings    REAL,
    equity      REAL
);

CREATE TABLE IF NOT EXISTS holdings (
    symbol      TEXT PRIMARY KEY,
    lots        INTEGER,
    avg_price   REAL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    metric      TEXT NOT NULL,      -- price | rsi
    op          TEXT NOT NULL,      -- below | above
    threshold   REAL NOT NULL,
    note        TEXT,
    active      INTEGER DEFAULT 1,
    last_fired  TEXT
);
"""


_PRAGMA_DONE = False


@contextmanager
def connect():
    # timeout: wait (don't crash) if another writer holds the lock — fixes
    # "unable to open database file" during bursty refresh + auto-refresh.
    conn = sqlite3.connect(db_path(), timeout=30.0)
    conn.row_factory = sqlite3.Row
    global _PRAGMA_DONE
    if not _PRAGMA_DONE:
        try:
            conn.execute("PRAGMA journal_mode=WAL")     # concurrent read+write
            conn.execute("PRAGMA busy_timeout=30000")   # 30s wait on lock
            conn.execute("PRAGMA synchronous=NORMAL")
            _PRAGMA_DONE = True
        except sqlite3.Error:
            pass
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate(conn) -> None:
    """Add columns introduced after initial release (idempotent)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(fundamentals)")}
    new = {
        "pe": "REAL", "pb": "REAL", "roe": "REAL", "debt_to_equity": "REAL",
        "payout_ratio": "REAL", "earnings_growth": "REAL", "dividend_yield": "REAL",
        "ex_dividend_date": "TEXT",
    }
    for name, typ in new.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE fundamentals ADD COLUMN {name} {typ}")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def upsert_security(symbol: str, name: str = "", sector: str = "",
                    is_index: bool = False, active: bool = True) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO securities(symbol,name,sector,is_index,active)
               VALUES(?,?,?,?,?)
               ON CONFLICT(symbol) DO UPDATE SET
                 name=excluded.name, sector=excluded.sector,
                 is_index=excluded.is_index, active=excluded.active""",
            (symbol, name, sector, int(is_index), int(active)),
        )


def save_prices(symbol: str, df: pd.DataFrame) -> int:
    """df indexed by date with columns open/high/low/close/volume."""
    if df is None or df.empty:
        return 0
    rows = []
    for dt, r in df.iterrows():
        d = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]
        rows.append((symbol, d, _f(r.get("open")), _f(r.get("high")),
                     _f(r.get("low")), _f(r.get("close")), _f(r.get("volume"))))
    dates = [r[1] for r in rows]
    dmin, dmax = min(dates), max(dates)
    with connect() as conn:
        # Replace the whole fetched window for this symbol: delete every existing
        # row inside [dmin, dmax] first, then insert exactly what the source
        # returned. A plain upsert (ON CONFLICT) only OVERWRITES matching dates,
        # so stale rows the source no longer reports — e.g. bars left over from
        # the synthetic seed on IDX market holidays (Christmas, Lebaran, CNY),
        # which yfinance never returns — would linger forever and spike the chart.
        # Deleting the window first removes them; history OUTSIDE the window is
        # untouched. (yfinance returns only real trading days, so this is safe.)
        conn.execute("DELETE FROM prices WHERE symbol=? AND date BETWEEN ? AND ?",
                     (symbol, dmin, dmax))
        conn.executemany(
            """INSERT INTO prices(symbol,date,open,high,low,close,volume)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(symbol,date) DO UPDATE SET
                 open=excluded.open, high=excluded.high, low=excluded.low,
                 close=excluded.close, volume=excluded.volume""",
            rows,
        )
    return len(rows)


def save_fundamentals(symbol: str, data: dict) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO fundamentals(symbol,price,market_cap,beta,last_dividend,
                   range_52w,sector,industry,pe,pb,roe,debt_to_equity,payout_ratio,
                   earnings_growth,dividend_yield,ex_dividend_date,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(symbol) DO UPDATE SET
                 price=excluded.price, market_cap=excluded.market_cap,
                 beta=excluded.beta, last_dividend=excluded.last_dividend,
                 range_52w=excluded.range_52w, sector=excluded.sector,
                 industry=excluded.industry, pe=excluded.pe, pb=excluded.pb,
                 roe=excluded.roe, debt_to_equity=excluded.debt_to_equity,
                 payout_ratio=excluded.payout_ratio,
                 earnings_growth=excluded.earnings_growth,
                 dividend_yield=excluded.dividend_yield,
                 ex_dividend_date=excluded.ex_dividend_date,
                 updated_at=excluded.updated_at""",
            (symbol, _f(data.get("price")), _f(data.get("market_cap")),
             _f(data.get("beta")), _f(data.get("last_dividend")),
             data.get("range_52w"), data.get("sector"), data.get("industry"),
             _f(data.get("pe")), _f(data.get("pb")), _f(data.get("roe")),
             _f(data.get("debt_to_equity")), _f(data.get("payout_ratio")),
             _f(data.get("earnings_growth")), _f(data.get("dividend_yield")),
             data.get("ex_dividend_date"), data.get("updated_at")),
        )


def log_refresh(source: str, symbols: int, rows: int, status: str, message: str = "") -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO refresh_log(run_at,source,symbols,rows,status,message) "
            "VALUES(datetime('now'),?,?,?,?,?)",
            (source, symbols, rows, status, message),
        )


def save_signals(run_date: str, recs: list) -> int:
    """recs: list of dicts (Recommendation.as_row()). Upserts by (run_date,symbol)."""
    cols = ["symbol", "action", "composite", "fundamental_score", "technical_score",
            "close", "div_yield_pct", "rsi", "trend", "range_pos_pct", "entry",
            "target", "stop", "lots", "est_cost_idr", "rationale"]
    rows = [tuple([run_date] + [r.get(c) for c in cols]) for r in recs]
    placeholders = ",".join(["?"] * (len(cols) + 1))
    with connect() as conn:
        conn.executemany(
            f"INSERT INTO signals(run_date,{','.join(cols)}) VALUES({placeholders}) "
            f"ON CONFLICT(run_date,symbol) DO UPDATE SET " +
            ",".join(f"{c}=excluded.{c}" for c in cols),
            rows,
        )
    return len(rows)


def load_signals(run_date: str | None = None) -> pd.DataFrame:
    with connect() as conn:
        if run_date is None:
            row = conn.execute("SELECT MAX(run_date) AS d FROM signals").fetchone()
            run_date = row["d"] if row else None
        if not run_date:
            return pd.DataFrame()
        df = pd.read_sql_query(
            "SELECT * FROM signals WHERE run_date=?", conn, params=(run_date,))
    return df


def latest_signal_date() -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT MAX(run_date) AS d FROM signals").fetchone()
    return row["d"] if row and row["d"] else None


def get_state(key: str, default: float = 0.0) -> float:
    with connect() as conn:
        row = conn.execute("SELECT value FROM paper_state WHERE key=?", (key,)).fetchone()
    return float(row["value"]) if row else default


def set_state(key: str, value: float) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO paper_state(key,value) VALUES(?,?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def get_positions() -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM paper_positions").fetchall()]


def upsert_position(symbol, lots, avg_price, opened_date, target, stop) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO paper_positions(symbol,lots,avg_price,opened_date,target,stop) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
            "lots=excluded.lots, avg_price=excluded.avg_price, target=excluded.target, "
            "stop=excluded.stop",
            (symbol, lots, avg_price, opened_date, target, stop))


def delete_position(symbol: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM paper_positions WHERE symbol=?", (symbol,))


def add_trade(trade_date, symbol, side, lots, price, value, reason) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO paper_trades(trade_date,symbol,side,lots,price,value,reason) "
                     "VALUES(?,?,?,?,?,?,?)",
                     (trade_date, symbol, side, lots, price, value, reason))


def record_equity(date, cash, holdings, equity) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO paper_equity(date,cash,holdings,equity) VALUES(?,?,?,?) "
                     "ON CONFLICT(date) DO UPDATE SET cash=excluded.cash, "
                     "holdings=excluded.holdings, equity=excluded.equity",
                     (date, cash, holdings, equity))


def load_trades() -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query("SELECT * FROM paper_trades ORDER BY trade_date DESC", conn)


def load_equity_curve() -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM paper_equity ORDER BY date", conn)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def set_holding(symbol: str, lots: int, avg_price: float, note: str = "") -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO holdings(symbol,lots,avg_price,note) VALUES(?,?,?,?) "
            "ON CONFLICT(symbol) DO UPDATE SET lots=excluded.lots, "
            "avg_price=excluded.avg_price, note=excluded.note",
            (symbol, int(lots), float(avg_price), note))


def list_holdings() -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM holdings ORDER BY symbol")]


def delete_holding(symbol: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM holdings WHERE symbol=?", (symbol,))


def clear_holdings() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM holdings")


def add_alert(symbol: str, metric: str, op: str, threshold: float, note: str = "") -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO alerts(symbol,metric,op,threshold,note,active) "
            "VALUES(?,?,?,?,?,1)", (symbol, metric, op, float(threshold), note))


def list_alerts(active_only: bool = False) -> list[dict]:
    with connect() as conn:
        q = "SELECT * FROM alerts"
        if active_only:
            q += " WHERE active=1"
        q += " ORDER BY id DESC"
        return [dict(r) for r in conn.execute(q).fetchall()]


def delete_alert(alert_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))


def mark_alert_fired(alert_id: int, when: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE alerts SET last_fired=? WHERE id=?", (when, alert_id))


def load_prices(symbol: str) -> pd.DataFrame:
    with connect() as conn:
        df = pd.read_sql_query(
            "SELECT date,open,high,low,close,volume FROM prices "
            "WHERE symbol=? ORDER BY date", conn, params=(symbol,))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    return df


def load_fundamentals(symbol: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM fundamentals WHERE symbol=?", (symbol,)).fetchone()
    return dict(row) if row else {}


def list_symbols(include_index: bool = False) -> list[str]:
    with connect() as conn:
        q = "SELECT symbol FROM securities WHERE active=1"
        if not include_index:
            q += " AND is_index=0"
        q += " ORDER BY symbol"
        return [r["symbol"] for r in conn.execute(q).fetchall()]


def load_security_names() -> dict:
    """{symbol: company name} for all securities (for display / hover labels)."""
    with connect() as conn:
        return {r["symbol"]: r["name"]
                for r in conn.execute("SELECT symbol, name FROM securities").fetchall()}


def last_refresh() -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM refresh_log ORDER BY run_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def _f(v):
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None
