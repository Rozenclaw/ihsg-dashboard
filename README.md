# IHSG Personal Dashboard — Phase 0–1

A private, single-user dashboard for the Indonesia Stock Exchange (IHSG / IDX
Composite). This is **Phase 0–1** of the PRD: the **data layer** + a
**read-only dashboard**. No recommendations, automation, or trading yet — those
are Phases 2–4.

> ⚠️ **Not financial advice.** Educational/personal tooling only. Market data via
> Yahoo Finance is unofficial and may be delayed or imperfect.

---

## What this gives you

- A **SQLite database** of daily OHLCV history for the IHSG index (`^JKSE`) and a
  curated universe of liquid IDX stocks (LQ45 + popular dividend names).
- **Technical indicators** computed locally: SMA(50/200), RSI(14), Bollinger Bands.
- A **Streamlit dashboard** with:
  - IHSG header (level, % change, RSI, trend, 52-week range position)
  - Watchlist table (close, change %, RSI, trend, range position, dividend yield)
  - Stock detail view: candlestick + SMA + Bollinger + RSI subplot, plus fundamentals
- A **pluggable data-source layer** (`yfinance` live, `synthetic` offline) so you
  can add iTick/FMP/GoAPI later without touching the UI.

---

## Project layout

```
ihsg_dashboard/
├── config.yaml              # all settings (data source, indicators, watchlist)
├── requirements.txt
├── data/                    # SQLite db + optional universe.csv (gitignored)
├── src/
│   ├── config.py            # config loader
│   ├── db.py                # SQLite schema + read/write helpers
│   ├── universe.py          # IHSG ticker universe (seed + full-CSV loader)
│   ├── indicators.py        # SMA / RSI / Bollinger + snapshot
│   ├── strategy.py          # Phase 2: dividend+value scoring -> BUY/HOLD/SELL
│   ├── live.py              # iTick realtime quote overlay (free tier)
│   ├── fetch.py             # orchestrates fetch -> DB
│   └── datasources/
│       ├── base.py          # DataSource interface (add providers here)
│       ├── yfinance_source.py
│       └── synthetic_source.py   # offline test data (no network)
├── scripts/
│   ├── refresh_data.py      # CLI: pull data into the DB
│   ├── recommend.py         # CLI: run strategy -> store + print signals
│   ├── selftest.py          # offline end-to-end smoke test
│   ├── test_live.py         # offline test for the iTick live module (mocked)
│   └── test_strategy.py     # offline end-to-end test for Phase 2
└── app/
    └── dashboard.py         # Streamlit read-only dashboard
```

---

## Quick start (on your own machine — needs internet)

```bash
cd ihsg_dashboard
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1) Pull data (seed universe, ~75 liquid stocks + IHSG). Takes a few minutes.
python scripts/refresh_data.py

# 2) Launch the dashboard
streamlit run app/dashboard.py
```

The dashboard opens at http://localhost:8501.

### Try it offline first (no internet needed)
```bash
python scripts/selftest.py                       # verifies the whole pipeline
python scripts/refresh_data.py --source synthetic --limit 10
streamlit run app/dashboard.py                   # view synthetic data
```

---

## Common commands

| Goal | Command |
|---|---|
| Refresh seed universe (live) | `python scripts/refresh_data.py` |
| Quick test run (5 symbols) | `python scripts/refresh_data.py --limit 5` |
| Offline/demo data | `python scripts/refresh_data.py --source synthetic` |
| Full universe (see below) | `python scripts/refresh_data.py --full` |
| Skip fundamentals (faster) | `python scripts/refresh_data.py --no-fundamentals` |
| Self-test (no network) | `python scripts/selftest.py` |

---

## Expanding to the FULL IHSG (~900 stocks)

The seed list covers the most liquid names. To cover the entire market:

1. Go to the IDX listed-companies page (https://www.idx.co.id) and export the
   company list.
2. Save it as `data/universe.csv` with a header row:
   ```csv
   symbol,name,sector
   BBRI,Bank Rakyat Indonesia,Financials
   PTBA,Bukit Asam,Energy
   ...
   ```
   (Bare codes are fine — `.JK` is appended automatically.)
3. Run `python scripts/refresh_data.py --full`.

> Pulling ~900 tickers from Yahoo takes a while and may hit soft rate limits.
> The `request_pause_sec` setting in `config.yaml` adds politeness delay. Start
> with the seed universe; expand once you're happy.

---

## Live quotes (iTick realtime overlay) 🔴

The EOD data above is daily/delayed. To add a **near-realtime** quote panel that
auto-refreshes during IDX hours, the dashboard can pull live prices from
[iTick](https://itick.org) (free tier).

**Setup (2 minutes):**

1. Sign up free at https://itick.org and copy your **API token**.
2. Give the token to the app one of two ways:

   **Option A — environment variable** (quick, per-terminal):
   ```bash
   export ITICK_TOKEN="paste_your_key_here"
   streamlit run app/dashboard.py
   ```

   **Option B — secrets file** (persists, recommended):
   create `.streamlit/secrets.toml` in the project folder with:
   ```toml
   ITICK_TOKEN = "paste_your_key_here"
   ```

3. Launch the dashboard. The **🔴 Live quotes** panel under the watchlist will
   show last/open/high/low/volume and auto-refresh every 60s (configurable).

**Notes**
- iTick uses bare IDX codes (e.g. `BBRI`); the app strips `.JK` automatically.
- Free tier is rate-limited — keep the watchlist small (≤ ~15) and the poll
  interval ≥ 60s. Tune via `live.poll_seconds` / `live.max_symbols` in `config.yaml`.
- No key? The panel simply shows a hint and the rest of the dashboard works fine.
- IDX trades ~09:00–16:00 WIB; outside those hours "live" = last session's close.
- Verify the module without a key/network: `python scripts/test_live.py`.

## Daily recommendations — Dividend + Value (Phase 2) 📋

The dashboard now includes a **ranked BUY / HOLD / SELL table**. For each stock it
computes:

- **Fundamental score (0–100)** — dividend yield (gated at `min_yield_pct`),
  plus a value proxy (52-week range position) and a low-beta bonus.
- **Technical score (0–100)** — trend (SMA50 vs SMA200), RSI timing
  (rewards oversold/normalizing, penalizes overbought), support proximity
  (near 52w low / below lower Bollinger), and volume confirmation.
- **Composite** = `0.6 × fundamental + 0.4 × technical` (weights configurable).

It then assigns an action and, for BUYs, concrete levels:

- **Entry** — at/near support (midway between close and lower Bollinger).
- **Target** — `+target_pct` above entry (default +20%).
- **Stop** — `−stop_pct` below entry (default −8%).
- **Lots** — risk-based size (caps loss to `risk_per_trade_pct` of portfolio at
  the stop; also capped by `max_position_pct`), rounded to IDX lots (100 shares).

**Run it from the CLI:**
```bash
python scripts/recommend.py            # evaluate universe, store + print top 20
python scripts/recommend.py --top 15   # show more/fewer
```
Or just open the dashboard — the recommendations section runs live and the CLI
additionally **stores a dated snapshot** in the `signals` table (history for
Phase 3 backtesting).

**Tuning:** every threshold lives under `strategy:` in `config.yaml`
(yield gate, buy/sell thresholds, RSI bands, target/stop %, risk sizing,
`portfolio_idr`). Defaults are starting points — tune with the backtest in Phase 3.

> ⚠️ These are **model levels for decision-support, not financial advice.** The
> dividend gate reduces—but does not eliminate—"yield traps"; always sanity-check
> before acting. Proper dividend-history and payout checks come in a later phase.

## Daily automation, paper trading & backtest (Phase 3) 🤖

### Hands-off daily job
`scripts/daily_job.py` runs the whole pipeline once: **refresh data → evaluate
strategy + store signals → advance the paper portfolio → send a digest**. It
skips weekends automatically (IDX closed).

```bash
python scripts/daily_job.py                 # full run (after IDX close)
python scripts/daily_job.py --no-refresh    # reuse existing data
python scripts/daily_job.py --source synthetic --force   # offline test
```

### Make it run automatically (even with the app closed)

**Option A — Mac/Linux cron (laptop must be on at run time):**
```bash
crontab -e
# 09:30 UTC = 16:30 WIB, Mon–Fri (after IDX close):
30 9 * * 1-5  /full/path/to/ihsg_dashboard/scripts/run_daily.sh
```

**Option B — GitHub Actions (runs in the cloud, laptop can be off):** ✅ best
A workflow is included at `.github/workflows/daily.yml`. Push the project to a
(private) GitHub repo, then add your secrets under **Settings → Secrets and
variables → Actions**: `ITICK_TOKEN`, `ITICK_HOST`, and any of
`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` / `SMTP_*` / `EMAIL_TO`. It runs
Mon–Fri at 09:30 UTC and caches the SQLite DB between runs so history builds up.

### Notifications (optional, free)
Set these as env vars or in `.streamlit/secrets.toml` to receive the daily digest:
- **Telegram:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **Email (SMTP):** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_TO`

If none are set, the job still runs and just skips sending.

### Paper trading (validate before real money)
A virtual portfolio simulates fills from the signals (buys top BUYs by score,
exits on target/stop/SELL), tracks cash, positions, P/L and an equity curve —
all in the **💼 Paper portfolio** section of the dashboard (with Advance/Reset
buttons), or advanced automatically by the daily job. Starting capital and fees
are set under `paper:` in `config.yaml`.

### Backtest
`scripts/backtest.py` (and the **🧪 Backtest** dashboard section) walk historical
bars applying the strategy, reporting total return, CAGR, max drawdown, Sharpe,
and comparison vs buy-and-hold IHSG.
```bash
python scripts/backtest.py --lookback 504 --rebalance 5 --max-positions 10
```
> Indicative only: dividend/beta fundamentals aren't point-in-time on the free
> tier, so the backtest mainly reflects the **technical timing** component.

## Deeper fundamentals, yield-trap flag & alerts (Tier 1) 🧠🔔

**Richer fundamentals** — the data layer now pulls P/E, P/B, ROE, debt/equity,
payout ratio, earnings growth and reported dividend yield (all free from Yahoo).
The fundamental score is now a real blend: **Dividend (0–45) + Value (P/E, P/B,
0–30) + Quality (ROE, leverage, beta, 0–25)** instead of a price-range proxy.

**Yield-trap flag** ⚠️ — a stock is flagged when its dividend looks
unsustainable (payout > `max_payout_pct`, or earnings falling, or very high
debt). Flagged stocks get a 50% fundamental-score penalty and a visible warning
in the Top-3 cards and stock detail. This is the single most important guard for
a dividend strategy. Tune `strategy.max_payout_pct` in `config.yaml`.

**Price / RSI alerts** 🔔 — set alerts like "BBRI price below 4000" or "PTBA RSI
below 35" in the dashboard (under the watchlist). The daily job checks them and
includes any triggers in your Telegram/email digest, de-duplicated per day.

```bash
python scripts/test_tier1.py   # offline test for all three
```

## Configuration (`config.yaml`)

- `data.source` — `yfinance` (live) or `synthetic` (offline test)
- `data.history_period` — how much history to pull (e.g. `2y`); 200+ days needed
  for SMA200
- `indicators.*` — SMA/RSI/Bollinger periods
- `dashboard.default_watchlist` — tickers shown by default

---

## Adding another free data source later

Implement the `DataSource` interface in `src/datasources/base.py`
(`history()` and optionally `fundamentals()`), register it in
`src/datasources/__init__.py`, and point `config.yaml` at it. The DB, indicators,
and dashboard need no changes. Planned adapters per the PRD: **iTick** (realtime
quote overlay), **FMP free** (fundamentals/dividends/DCF), **GoAPI/Sectors.app**.

---

## What's next (per PRD)

- **Phase 2 ✅ DONE** — dividend+value gate + technical triggers → daily
  BUY/HOLD/SELL with entry/target/stop/position size (`src/strategy.py`,
  `scripts/recommend.py`, dashboard section, `signals` table).
- **Phase 3 ✅ DONE** — daily automation job, cron + GitHub Actions schedulers,
  paper-trading engine, backtest, Telegram/email digest (`src/paper.py`,
  `src/backtest.py`, `src/notify.py`, `scripts/daily_job.py`,
  `.github/workflows/daily.yml`).
- ~~**Phase 3** — daily automation (scheduled task / GitHub Actions), paper-trading~~
  engine, backtest, Telegram/email digest.
- **Phase 3.5** — assisted execution (order-ticket generator → you confirm in broker).
- **Phase 4** — real execution adapter *only if* a legitimate channel exists
  (see PRD §3 & §9; not available for free retail on IDX today).

---

## Notes & limitations

- Yahoo Finance is unofficial; treat data as best-effort. The adapter design lets
  you swap in a more authoritative source later.
- This sandbox/build environment has no outbound internet, so live fetches were
  verified by code review + an offline synthetic end-to-end test
  (`scripts/selftest.py`). Run the live refresh on your own machine.
- Dividend yield in the watchlist is a rough trailing estimate
  (`last_dividend / price`); Phase 2 adds proper dividend-history-based yield and
  yield-trap checks.
```
