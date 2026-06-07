"""Daily-trading shortlist engine — beginner-safe, liquid-universe swing method.

WHAT THIS IS (and isn't): a *daily-refreshed shortlist* of liquid IDX names that
look like reasonable short-term swing entries, with strict, mechanical risk
control. It is NOT intraday scalping — research is consistent that scalping/day-
trading is the *least* safe choice for a beginner on a small budget, while a
disciplined swing/pullback method on liquid blue chips is materially safer and
more sustainable. So "daily" here = "a fresh ranking you check each day", not
"trade every minute". Each position is still held for days to weeks.

Method ("Daily Liquid Swing Shortlist"), all deterministic from the stored daily
OHLCV snapshot:
  1. Universe   -> only liquid names (avg daily turnover gate); illiquid rejected.
  2. Day-score  -> trend alignment + momentum + RSI timing + pullback + volume,
                   five buckets summing to 100.
  3. Safety     -> filters (illiquid / too volatile / below SMA200 / short
                   history / overbought) downgrade a name to WATCH or AVOID; a
                   BUY is never issued without a defined long-term (SMA200) trend.
  4. Levels     -> entry = last close; ATR-based stop clamped to 3-8% risk;
                   target at R:R = 2.
  5. Simulation -> split a limited DAILY BUDGET across the BUY picks in whole IDX
                   lots (100 shares), never exceeding budget, and show NET
                   gain/loss after realistic costs (fees + 0.1% sell tax).

Thresholds live in config.yaml `daytrade.*`. Decision-support only — NOT
financial advice, and signals are candidates for your own review, not buy
instructions.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import allocate, db, indicators, strategy

LOT = strategy.LOT_SIZE  # 100 shares / lot on IDX
MIN_BARS = 220           # need >= SMA200 + buffer before a name can be a BUY


# ----------------------------- config -------------------------------------

def _params(cfg: dict) -> dict:
    p = {
        "top_n": 10,                  # size of the shortlist
        "min_turnover_idr": 5e9,      # liquidity gate: avg daily value traded
        "atr_period": 14,
        "atr_mult_stop": 1.5,         # stop = entry - mult*ATR ...
        "min_stop_pct": 3.0,          # ... but never tighter than this (whipsaw)
        "max_stop_pct": 8.0,          # ... and never risk more than this
        "atr_max_pct": 7.0,           # too volatile for a beginner -> AVOID
        "rr_target": 2.0,             # target distance = RR * stop distance
        "rsi_overbought": 70.0,       # don't chase above this (score 0, never BUY)
        "buy_score": 60.0,            # score >= -> BUY (if filters pass)
        "watch_score": 45.0,          # score >= -> WATCH
        "risk_warn_pct": 2.0,         # warn if a day's total risk exceeds this % of capital
        "buy_fee_bps": 15.0,          # broker fee on buy  (~0.15%)
        "sell_fee_bps": 25.0,         # broker fee + 0.1% sell tax on sell (~0.25%)
        "default_capital_idr": 10_000_000,    # total trading capital (sim default)
        "default_daily_budget_idr": 1_000_000,  # today's budget (sim default)
    }
    p.update(cfg.get("daytrade", {}) or {})
    return p


def round_trip_pct(p: dict) -> float:
    """Approx % the price must rise just to cover one round-trip's costs."""
    return (p["buy_fee_bps"] + p["sell_fee_bps"]) / 100.0


# ----------------------------- math helpers -------------------------------

def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _atr(df: pd.DataFrame, period: int) -> float | None:
    """Average True Range over the last `period` bars (simple mean of TR)."""
    if df is None or len(df) < period + 1:
        return None
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean().iloc[-1]
    return float(atr) if pd.notna(atr) else None


def _ret_pct(close: pd.Series, n: int) -> float | None:
    """Return over the last n bars, in %."""
    if len(close) < n + 1:
        return None
    a, b = close.iloc[-1], close.iloc[-(n + 1)]
    return float((a - b) / b * 100) if b else None


# ----------------------------- per-stock metrics --------------------------

def _metrics(symbol: str, cfg: dict, p: dict) -> dict | None:
    """Compute the day-trade metric snapshot for one symbol, or None if there
    isn't enough clean history."""
    df = indicators.enrich(db.load_prices(symbol), cfg)
    if df is None or df.empty or len(df) < 60:
        return None
    bars = len(df)
    last = df.iloc[-1]
    close = float(last["close"]) if pd.notna(last["close"]) else None
    if not close or close <= 0:
        return None

    # Resolve the fast/slow SMA column names from config (indicators.enrich names
    # them sma{fast}/sma{slow}); don't hard-code "sma50"/"sma200".
    ind = cfg.get("indicators", {})
    fast_col, slow_col = f"sma{ind.get('sma_fast', 50)}", f"sma{ind.get('sma_slow', 200)}"
    sma20_series = df["close"].rolling(20, min_periods=20).mean()
    sma20 = float(sma20_series.iloc[-1]) if pd.notna(sma20_series.iloc[-1]) else None
    sma50 = float(last[fast_col]) if pd.notna(last.get(fast_col)) else None
    sma200 = float(last[slow_col]) if pd.notna(last.get(slow_col)) else None
    rsi = float(last["rsi"]) if pd.notna(last.get("rsi")) else None
    vol = float(last["volume"]) if pd.notna(last.get("volume")) else None
    vavg = float(last["vol_avg20"]) if pd.notna(last.get("vol_avg20")) else None
    atr = _atr(df, int(p["atr_period"]))

    # Is the SMA20 support trending up over the last week?
    sma20_prev = sma20_series.iloc[-6] if len(sma20_series) >= 6 else np.nan
    sma20_rising = bool(pd.notna(sma20_prev) and sma20 is not None and sma20 > float(sma20_prev))

    turnover = close * vavg if vavg else 0.0
    vol_ratio = (vol / vavg) if (vol and vavg) else None
    atr_pct = (atr / close * 100) if atr else None
    # 52w range position only meaningful with ~1y of bars.
    range_pos = None
    if bars >= 200:
        hi = float(df["close"].tail(252).max())
        lo = float(df["close"].tail(252).min())
        range_pos = ((close - lo) / (hi - lo) * 100) if hi > lo else None

    return {
        "symbol": symbol, "bars": bars, "close": close, "sma20": sma20,
        "sma50": sma50, "sma200": sma200, "sma20_rising": sma20_rising, "rsi": rsi,
        "atr": atr, "atr_pct": atr_pct, "vol": vol, "vol_avg20": vavg,
        "vol_ratio": vol_ratio, "turnover": turnover,
        "ret_5d": _ret_pct(df["close"], 5), "ret_20d": _ret_pct(df["close"], 20),
        "range_pos_pct": range_pos,
    }


# ----------------------------- scoring ------------------------------------

def _score(m: dict, p: dict) -> tuple[float, dict]:
    """Day-score 0..100 with a per-component breakdown (buckets sum to 100)."""
    close, sma20, sma50, sma200 = m["close"], m["sma20"], m["sma50"], m["sma200"]

    # Trend alignment (0..30).
    trend = 0.0
    if sma20 and close > sma20:
        trend += 8
    if sma20 and sma50 and sma20 > sma50:
        trend += 8
    if sma50 and sma200 and sma50 > sma200:
        trend += 8
    if sma200 and close > sma200:
        trend += 6
    trend = _clamp(trend, 0, 30)

    # Momentum (0..20): reward mild 20d strength, penalize over-extension.
    mom = 0.0
    r20, r5 = m["ret_20d"], m["ret_5d"]
    if r20 is not None:
        mom += _clamp(r20 / 15 * 16, 0, 16)
        if r20 > 25:                       # chasing a parabolic move
            mom -= _clamp((r20 - 25) / 10 * 16, 0, 16)
    if r5 is not None and r5 > 0:
        mom += 4
    mom = _clamp(mom, 0, 20)

    # RSI timing (0..20): peak ~52, decay to edges, HARD 0 above the
    # overbought line so the score never rewards chasing.
    rsi = m["rsi"]
    if rsi is None:
        rsi_s = 10.0
    elif rsi > p["rsi_overbought"]:
        rsi_s = 0.0
    else:
        rsi_s = _clamp(20 - abs(rsi - 52) * 0.9, 0, 20)

    # Pullback quality (0..15): close just above a rising SMA20 is ideal.
    pull = 7.0
    if sma20:
        d = (close - sma20) / sma20 * 100
        if -2 <= d <= 4:
            pull = 15 - abs(d - 1) * 2
        elif d > 4:
            pull = 15 - (d - 4) * 1.5
        else:
            pull = 8 + (d + 2)
        if not m["sma20_rising"]:
            pull *= 0.6                     # support not trending up -> weaker
    pull = _clamp(pull, 0, 15)

    # Volume confirmation (0..15).
    vr = m["vol_ratio"]
    vol_s = _clamp(((vr if vr is not None else 0.8) - 0.8) / 1.2 * 15, 0, 15)

    total = _clamp(trend + mom + rsi_s + pull + vol_s, 0, 100)
    parts = {"trend": round(trend, 1), "momentum": round(mom, 1),
             "rsi": round(rsi_s, 1), "pullback": round(pull, 1),
             "volume": round(vol_s, 1)}
    return round(total, 1), parts


def _flags(m: dict, p: dict) -> list[str]:
    """Safety flags. A HARD flag forces AVOID; a soft one blocks BUY (-> WATCH)."""
    f = []
    if m["turnover"] < p["min_turnover_idr"]:
        f.append("illiquid")
    if m["atr_pct"] is not None and m["atr_pct"] > p["atr_max_pct"]:
        f.append("volatile")
    if m["sma200"] is None or m["bars"] < MIN_BARS:
        f.append("short history")          # can't *confirm* long-term trend
    if m["sma200"] is not None and m["close"] < m["sma200"]:
        f.append("below SMA200")           # trend is computable AND broken (HARD)
    if m["rsi"] is not None and m["rsi"] > p["rsi_overbought"]:
        f.append("overbought")
    return f


_HARD = {"illiquid", "volatile", "below SMA200"}   # -> AVOID outright
_SOFT = {"short history", "overbought"}            # -> never BUY, can be WATCH


def _signal(score: float, flags: list[str], m: dict, p: dict) -> str:
    if _HARD & set(flags):
        return "AVOID"
    above_50 = m["sma50"] is None or m["close"] >= m["sma50"]
    if score >= p["buy_score"] and not (_SOFT & set(flags)) and above_50:
        return "BUY"
    if score >= p["watch_score"]:
        return "WATCH"
    return "AVOID"


# ----------------------------- levels -------------------------------------

def _levels(m: dict, p: dict) -> dict:
    """Entry / stop / target with risk bounded to [min_stop_pct, max_stop_pct].

    entry = last close (a market entry, so the plan can actually fill). The stop
    is ATR-based but clamped so per-trade risk is always 3-8%."""
    entry = m["close"]
    atr = m["atr"]
    atr_stop = entry - p["atr_mult_stop"] * atr if atr else entry * (1 - p["max_stop_pct"] / 100)
    # cap risk at max_stop_pct (higher price = tighter stop) ...
    stop = max(atr_stop, entry * (1 - p["max_stop_pct"] / 100))
    # ... but keep at least min_stop_pct of room to avoid whipsaw.
    stop = min(stop, entry * (1 - p["min_stop_pct"] / 100))
    stop = round(stop, 2)
    risk_ps = entry - stop                          # exactly the placed stop distance
    target = round(entry + p["rr_target"] * risk_ps, 2)
    rr = (target - entry) / risk_ps if risk_ps > 0 else None
    return {"entry": round(entry, 2), "stop": stop, "target": target,
            "risk_ps": risk_ps, "rr": round(rr, 2) if rr else None,
            "stop_pct": round((entry - stop) / entry * 100, 1) if entry else None}


# ----------------------------- board --------------------------------------

def build_board(cfg: dict, *, lang: str = "EN", top_n: int | None = None,
                as_of: str | None = None, symbols: list[str] | None = None) -> dict:
    """Rank the universe into a daily-trading shortlist."""
    p = _params(cfg)
    n = int(top_n or p["top_n"])
    as_of = as_of or pd.Timestamp.today().strftime("%Y-%m-%d")
    # Screen the liquidity-capped set (not all ~950 stored names) so the board
    # builds fast; the daily turnover gate below still applies on top.
    syms = symbols if symbols is not None else strategy.screening_symbols(cfg)

    scored = []
    for s in syms:
        m = _metrics(s, cfg, p)
        if not m:
            continue
        score, parts = _score(m, p)
        flags = _flags(m, p)
        signal = _signal(score, flags, m, p)
        lv = _levels(m, p)
        scored.append({
            **{k: m[k] for k in ("symbol", "close", "rsi", "atr_pct", "turnover",
                                 "vol_ratio", "ret_5d", "ret_20d", "range_pos_pct",
                                 "sma20", "sma50", "sma200")},
            "score": score, "parts": parts, "flags": flags, "signal": signal,
            "entry": lv["entry"], "stop": lv["stop"], "target": lv["target"],
            "rr": lv["rr"], "risk_ps": lv["risk_ps"], "stop_pct": lv["stop_pct"],
            "why": _why(m, parts, flags, lang, p),
        })

    rank = {"BUY": 0, "WATCH": 1, "AVOID": 2}
    scored.sort(key=lambda r: (rank.get(r["signal"], 9), -r["score"]))
    rows = scored[:n]
    for i, r in enumerate(rows):
        r["rank"] = i + 1

    counts = {"BUY": 0, "WATCH": 0, "AVOID": 0}
    for r in scored:
        counts[r["signal"]] = counts.get(r["signal"], 0) + 1

    return {"as_of": as_of, "lang": lang, "rows": rows, "params": p,
            "universe_count": len(scored), "counts": counts,
            "breakeven_pct": round_trip_pct(p), "method": _method_label(lang)}


def _method_label(lang: str) -> dict:
    if lang == "ID":
        return {"name": "Daily Liquid Swing Shortlist",
                "summary": "Shortlist harian saham IDX paling likuid yang terlihat "
                           "sebagai entry swing jangka pendek yang wajar, dengan "
                           "risk control ketat. Ini bukan scalping intraday."}
    return {"name": "Daily Liquid Swing Shortlist",
            "summary": "A daily-refreshed shortlist of the most liquid IDX names "
                       "that look like reasonable short-term swing entries, with "
                       "strict risk control. This is not intraday scalping."}


def _why(m: dict, parts: dict, flags: list[str], lang: str, p: dict) -> list[str]:
    """Short bilingual bullet reasons for the row's signal."""
    ID = lang == "ID"
    out: list[str] = []
    rsi = m["rsi"]
    if parts["trend"] >= 22:
        out.append("Trend naik selaras (di atas SMA)." if ID else "Aligned uptrend (above SMAs).")
    elif parts["trend"] <= 8:
        out.append("Tren lemah / belum naik." if ID else "Weak / not-yet-up trend.")
    if rsi is not None:
        if rsi > p["rsi_overbought"]:
            out.append(f"RSI {rsi:.0f} overbought — tunggu pullback." if ID
                       else f"RSI {rsi:.0f} overbought — wait for a pullback.")
        elif 45 <= rsi <= 60:
            out.append(f"RSI {rsi:.0f} sehat (zona entry)." if ID
                       else f"RSI {rsi:.0f} healthy (entry zone).")
    if m["vol_ratio"] and m["vol_ratio"] >= 1.3:
        out.append(f"Volume {m['vol_ratio']:.1f}× rata-rata — minat beli nyata." if ID
                   else f"Volume {m['vol_ratio']:.1f}× average — real buying interest.")
    if "illiquid" in flags:
        out.append("Kurang likuid — sulit keluar, hindari." if ID
                   else "Not liquid enough — hard to exit, avoid.")
    if "volatile" in flags:
        out.append("Terlalu volatil untuk pemula." if ID else "Too volatile for a beginner.")
    if "below SMA200" in flags:
        out.append("Di bawah SMA200 — tren panjang patah." if ID
                   else "Below SMA200 — long-term trend broken.")
    if "short history" in flags:
        out.append("Histori terlalu pendek untuk konfirmasi tren panjang." if ID
                   else "History too short to confirm the long-term trend.")
    if not out:
        out.append("Setup netral — perlu konfirmasi lanjutan." if ID
                   else "Neutral setup — needs further confirmation.")
    return out


# ----------------------------- budget simulation --------------------------

def simulate_allocation(board: dict, budget_idr: float, *, num: int | None = None,
                        include_watch: bool = False,
                        capital_idr: float | None = None) -> dict:
    """Split a limited DAILY BUDGET across the board's BUY picks in whole lots.

    Reuses the lot-aware allocator (src/allocate.plan) by mapping the day-score
    onto its `composite` weight, then attaches each pick's entry/stop/target and
    the NET gain/loss after realistic costs (broker fee + 0.1% sell tax).
    """
    lang = board.get("lang", "EN")
    p = board.get("params") or {}
    buy_bps = float(p.get("buy_fee_bps", 15.0))
    sell_bps = float(p.get("sell_fee_bps", 25.0))
    wanted = {"BUY"} | ({"WATCH"} if include_watch else set())
    picks = [r for r in board["rows"] if r["signal"] in wanted]
    if num:
        picks = picks[:int(num)]
    levels = {r["symbol"]: r for r in picks}

    base = {"budget": float(budget_idr), "capital": capital_idr,
            "include_watch": include_watch}
    if not picks:
        note = ("Tidak ada sinyal BUY pada shortlist hari ini — sering kali langkah "
                "terbaik adalah tahan cash dan menunggu setup berikutnya. (Cash "
                "juga sebuah posisi.)" if lang == "ID" else
                "No BUY signals on today's shortlist — often the best move is to "
                "hold cash and wait for the next setup. (Cash is a position too.)")
        return {**base, "rows": [], "spent": 0.0, "leftover": float(budget_idr),
                "picks": 0, "note": note,
                "totals": {"capital": 0.0, "gain": 0.0, "loss": 0.0, "rr": None,
                           "gross_gain": 0.0, "gross_loss": 0.0, "costs": 0.0,
                           "risk_pct_capital": None}}

    df = pd.DataFrame([{"symbol": r["symbol"], "action": "BUY",
                        "composite": r["score"], "trend": "Uptrend",
                        "entry": r["entry"], "close": r["close"]} for r in picks])
    plan = allocate.plan(float(budget_idr), df, max_names=len(picks))

    rows = []
    for c in plan["rows"]:
        lv = levels[c["symbol"]]
        shares, entry, stop, target = c["shares"], lv["entry"], lv["stop"], lv["target"]
        capital = c["cost"]
        gross_gain = (target - entry) * shares
        gross_loss = (entry - stop) * shares
        buy_cost = entry * shares * buy_bps / 1e4
        sell_cost_t = target * shares * sell_bps / 1e4
        sell_cost_s = stop * shares * sell_bps / 1e4
        net_gain = gross_gain - buy_cost - sell_cost_t
        net_loss = gross_loss + buy_cost + sell_cost_s     # positive magnitude
        rows.append({
            "symbol": c["symbol"], "signal": lv["signal"], "score": lv["score"],
            "lots": c["lots"], "shares": shares, "entry": entry, "stop": stop,
            "target": target, "rr": lv["rr"], "capital": capital,
            "pct": c.get("pct"), "gain": net_gain, "loss": net_loss,
            "gross_gain": gross_gain, "gross_loss": gross_loss,
            "cost": buy_cost + sell_cost_t,
        })
    rows.sort(key=lambda r: -r["capital"])
    tot_cap = sum(r["capital"] for r in rows)
    tot_gain = sum(r["gain"] for r in rows)
    tot_loss = sum(r["loss"] for r in rows)
    tot_costs = sum(r["cost"] for r in rows)
    risk_pct_cap = (tot_loss / capital_idr * 100) if capital_idr else None
    warn_pct = float(p.get("risk_warn_pct", 2.0))
    totals = {"capital": tot_cap, "gain": tot_gain, "loss": tot_loss,
              "gross_gain": sum(r["gross_gain"] for r in rows),
              "gross_loss": sum(r["gross_loss"] for r in rows),
              "costs": tot_costs, "rr": (tot_gain / tot_loss) if tot_loss > 0 else None,
              "risk_pct_capital": risk_pct_cap, "risk_warn_pct": warn_pct,
              "risk_warn": (risk_pct_cap is not None and risk_pct_cap > warn_pct)}
    return {**base, "rows": rows, "spent": plan["spent"], "leftover": plan["leftover"],
            "picks": len(rows), "note": plan.get("note", ""), "totals": totals}


# ----------------------------- markdown -----------------------------------

def _f(x, dp: int = 0) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:,.{dp}f}"


def to_markdown(board: dict, sim: dict | None = None) -> str:
    """Bilingual report — AI grounding facts + downloadable note."""
    lang = board.get("lang", "EN")
    ID = lang == "ID"
    L: list[str] = []
    method = board.get("method", {})
    be = board.get("breakeven_pct")
    if ID:
        L.append("# Shortlist Trading Harian — Saham Likuid (Swing)")
        L.append(f"\n**Tanggal acuan:** {board['as_of']}  ")
        L.append(f"**Metode:** {method.get('name')} — {method.get('summary')}  ")
        L.append(f"**Universe dinilai:** {board['universe_count']} saham · "
                 f"BUY {board['counts'].get('BUY',0)} · WATCH {board['counts'].get('WATCH',0)} · "
                 f"AVOID {board['counts'].get('AVOID',0)}")
        L.append("\n> Catatan: alat bantu keputusan, BUKAN saran finansial. Sinyal "
                 "adalah kandidat untuk Anda tinjau sendiri, bukan instruksi beli. "
                 "'Harian' = shortlist yang di-refresh tiap hari (hold beberapa "
                 "hari–minggu), bukan scalping intraday.\n")
        L.append("## Shortlist (peringkat)\n")
        L.append("| # | Saham | Sinyal | Score | RSI | Entry | Stop | Target | R:R | Risk% |")
    else:
        L.append("# Daily Trading Shortlist — Liquid Stocks (Swing)")
        L.append(f"\n**As of:** {board['as_of']}  ")
        L.append(f"**Method:** {method.get('name')} — {method.get('summary')}  ")
        L.append(f"**Universe scored:** {board['universe_count']} stocks · "
                 f"BUY {board['counts'].get('BUY',0)} · WATCH {board['counts'].get('WATCH',0)} · "
                 f"AVOID {board['counts'].get('AVOID',0)}")
        L.append("\n> Note: decision-support, NOT financial advice. Signals are "
                 "candidates for your own review, not buy instructions. 'Daily' = a "
                 "shortlist refreshed each day (hold days–weeks), not intraday scalping.\n")
        L.append("## Shortlist (ranked)\n")
        L.append("| # | Stock | Signal | Score | RSI | Entry | Stop | Target | R:R | Risk% |")
    L.append("|--:|---|---|--:|--:|--:|--:|--:|--:|--:|")
    for r in board["rows"]:
        L.append(f"| {r['rank']} | {r['symbol']} | {r['signal']} | {_f(r['score'],1)} | "
                 f"{_f(r['rsi'],0)} | {_f(r['entry'])} | {_f(r['stop'])} | "
                 f"{_f(r['target'])} | {_f(r['rr'],2)}x | {_f(r['stop_pct'],1)}% |")
    buys = [r for r in board["rows"] if r["signal"] == "BUY"][:5]
    if buys:
        L.append(("\n### Alasan singkat (BUY teratas)\n" if ID else "\n### Why (top BUY names)\n"))
        for r in buys:
            L.append(f"- **{r['symbol']}** — " + "; ".join(r["why"]))
    if be:
        L.append((f"\n> ⚠️ Biaya: ±{be:.2f}% per putaran (beli+jual+pajak) — harga "
                  "harus naik segitu hanya untuk balik modal; sering trading "
                  "menggerus modal kecil." if ID else
                  f"\n> ⚠️ Costs: ±{be:.2f}% round-trip (buy+sell+tax) — price must "
                  "rise that much just to break even; frequent trading erodes a "
                  "small budget."))
    # simulation
    if sim and sim.get("rows"):
        t = sim["totals"]
        if ID:
            L.append(f"\n## Simulasi Alokasi Budget Harian (Rp{_f(sim['budget'])})\n")
            L.append("| Saham | Lot | Shares | Modal | % | Net Gain | Net Loss |")
        else:
            L.append(f"\n## Daily Budget Allocation Simulation (Rp{_f(sim['budget'])})\n")
            L.append("| Stock | Lots | Shares | Capital | % | Net Gain | Net Loss |")
        L.append("|---|--:|--:|--:|--:|--:|--:|")
        for r in sim["rows"]:
            L.append(f"| {r['symbol']} | {r['lots']} | {_f(r['shares'])} | "
                     f"Rp{_f(r['capital'])} | {_f(r['pct'],0)}% | Rp{_f(r['gain'])} | "
                     f"Rp{_f(r['loss'])} |")
        if ID:
            L.append(f"\n- **Terpakai:** Rp{_f(sim['spent'])} · **Sisa cash:** Rp{_f(sim['leftover'])}")
            L.append(f"- **Total net gain (di target):** Rp{_f(t['gain'])} "
                     f"(bruto Rp{_f(t['gross_gain'])}, biaya ±Rp{_f(t['costs'])})")
            L.append(f"- **Total net loss (semua kena stop):** Rp{_f(t['loss'])}")
            L.append(f"- **R:R portofolio (net):** {_f(t['rr'],2)}x")
            if t.get("risk_pct_capital") is not None:
                L.append(f"- **Risiko vs total modal:** {_f(t['risk_pct_capital'],1)}% "
                         "(idealnya kecil — pemula jaga ≤1–2% per hari)")
        else:
            L.append(f"\n- **Spent:** Rp{_f(sim['spent'])} · **Leftover cash:** Rp{_f(sim['leftover'])}")
            L.append(f"- **Total net gain (at target):** Rp{_f(t['gain'])} "
                     f"(gross Rp{_f(t['gross_gain'])}, costs ±Rp{_f(t['costs'])})")
            L.append(f"- **Total net loss (all stops hit):** Rp{_f(t['loss'])}")
            L.append(f"- **Portfolio R:R (net):** {_f(t['rr'],2)}x")
            if t.get("risk_pct_capital") is not None:
                L.append(f"- **Risk vs total capital:** {_f(t['risk_pct_capital'],1)}% "
                         "(keep it small — beginners ≤1–2% per day)")
    return "\n".join(L)
