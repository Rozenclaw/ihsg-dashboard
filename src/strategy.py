"""Phase 2 — Dividend + Value strategy engine.

Pipeline per stock:
  1. Fundamental gate  -> Fundamental Score 0..100  (dividend + value)
  2. Technical timing  -> Technical Score 0..100    (trend, RSI, support, volume)
  3. Composite         = w_f * Fund + w_t * Tech
  4. Action            -> BUY / HOLD / SELL  + entry, target, stop, lots, rationale

Everything is deterministic given the stored data snapshot. Thresholds live in
config.yaml (strategy.*) so they can be tuned without code changes.

IMPORTANT: decision-support only, not financial advice.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import pandas as pd

from . import db, indicators

LOT_SIZE = 100  # IDX: 1 lot = 100 shares


# ----------------------------- config helpers -----------------------------

def _strat(cfg: dict) -> dict:
    s = {
        "weight_fundamental": 0.6,
        "weight_technical": 0.4,
        "min_yield_pct": 4.0,         # dividend gate
        "good_yield_pct": 8.0,        # yield that scores ~full marks
        "max_payout_pct": 100.0,      # payout above this = yield-trap risk
        "buy_threshold": 60.0,        # composite >= -> BUY (if gate passed)
        "sell_threshold": 40.0,       # composite < -> SELL bias
        "rsi_oversold": 40.0,
        "rsi_overbought": 70.0,
        "target_pct": 20.0,           # default profit target above entry
        "stop_pct": 8.0,              # default stop below entry
        "risk_per_trade_pct": 1.5,    # % of portfolio risked per position
        "max_position_pct": 15.0,     # cap weight per name
        "portfolio_idr": 100_000_000, # assumed capital for sizing (tune in UI)
        "min_history_days": 60,       # need enough bars to be meaningful
    }
    s.update(cfg.get("strategy", {}) or {})
    return s


# ----------------------------- result object ------------------------------

@dataclass
class Recommendation:
    symbol: str
    action: str                # BUY | HOLD | SELL | SKIP
    composite: Optional[float]
    fundamental_score: Optional[float]
    technical_score: Optional[float]
    close: Optional[float]
    div_yield_pct: Optional[float]
    rsi: Optional[float]
    trend: str
    range_pos_pct: Optional[float]
    entry: Optional[float]
    target: Optional[float]
    stop: Optional[float]
    lots: Optional[int]
    est_cost_idr: Optional[float]
    rationale: str
    # Tier 1 additions:
    yield_trap: bool = False
    trap_reasons: str = ""
    pe: Optional[float] = None
    pb: Optional[float] = None
    roe: Optional[float] = None
    payout_ratio: Optional[float] = None
    earnings_growth: Optional[float] = None
    # Tier 2/3 additions:
    sector: Optional[str] = None
    sector_rank_pct: Optional[float] = None   # 0..100, higher = best in sector
    conviction: str = ""                       # high | medium | speculative
    ex_dividend_date: Optional[str] = None
    days_to_cum: Optional[int] = None

    def as_row(self) -> dict:
        return asdict(self)


# ----------------------------- scoring ------------------------------------

def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _r(v, dp: int = 1):
    """Round if numeric, else None."""
    return round(float(v), dp) if isinstance(v, (int, float)) else None


def _conviction(action: str, f_score: float, t_score: float) -> str:
    """Conviction band: do fundamentals and technicals agree?"""
    if action != "BUY":
        return ""
    strong_f, strong_t = f_score >= 60, t_score >= 60
    if strong_f and strong_t:
        return "high"
    if strong_f or strong_t:
        return "medium"
    return "speculative"


def _days_to_cum(ex_date: str | None) -> int | None:
    """Trading days-ish to cum-date (ex-date minus 1 business day)."""
    if not ex_date:
        return None
    try:
        ex = pd.Timestamp(ex_date)
        cum = ex - pd.tseries.offsets.BDay(1)
        return int((cum.normalize() - pd.Timestamp.today().normalize()).days)
    except Exception:
        return None


def _div_yield(fund: dict) -> float | None:
    """Prefer the provider's dividend_yield; fall back to lastDividend/price."""
    dy = fund.get("dividend_yield")
    if isinstance(dy, (int, float)) and dy > 0:
        return float(dy)
    price, div = fund.get("price"), fund.get("last_dividend")
    return (div / price * 100) if (div and price) else None


def detect_yield_trap(fund: dict, strat: dict) -> tuple[bool, list[str]]:
    """Flag dividends that look unsustainable. Returns (is_trap, reasons)."""
    reasons = []
    payout = fund.get("payout_ratio")
    eg = fund.get("earnings_growth")
    de = fund.get("debt_to_equity")
    if isinstance(payout, (int, float)) and payout > strat["max_payout_pct"]:
        reasons.append(f"payout {payout:.0f}% > {strat['max_payout_pct']:.0f}%")
    if isinstance(eg, (int, float)) and eg < -10:
        reasons.append(f"earnings falling {eg:.0f}%")
    if isinstance(de, (int, float)) and de > 200:
        reasons.append(f"high debt/equity {de:.0f}")
    # Trap if payout unsustainable, or earnings clearly shrinking while paying out.
    is_trap = bool(reasons) and (
        (isinstance(payout, (int, float)) and payout > strat["max_payout_pct"])
        or (isinstance(eg, (int, float)) and eg < -10))
    return is_trap, reasons


def fundamental_score(fund: dict, strat: dict) -> tuple[float, float | None, list[str]]:
    """Return (score 0..100, dividend_yield_pct, notes).

    Score = Dividend (0..45) + Value (0..30) + Quality (0..25), with a penalty
    if the dividend looks like a yield trap.
    """
    notes: list[str] = []
    dy = _div_yield(fund)
    if dy is None:
        notes.append("no dividend data")
        return 0.0, None, notes

    # --- Dividend component (0..45) ---
    lo, hi = strat["min_yield_pct"], strat["good_yield_pct"]
    if dy < lo:
        div_s = (dy / lo) * 15.0
        notes.append(f"yield {dy:.1f}% < gate {lo:.0f}%")
    else:
        div_s = 15.0 + _clamp((dy - lo) / max(hi - lo, 0.01) * 30.0, 0, 30)
        notes.append(f"yield {dy:.1f}%")

    # --- Value component (0..30): P/E and P/B, lower is better ---
    val_s = 0.0
    pe = fund.get("pe")
    if isinstance(pe, (int, float)) and pe > 0:
        # 8x or below -> full marks; 25x+ -> ~0
        val_s += _clamp((25 - pe) / (25 - 8) * 18.0, 0, 18)
        notes.append(f"P/E {pe:.1f}")
    pb = fund.get("pb")
    if isinstance(pb, (int, float)) and pb > 0:
        val_s += _clamp((3 - pb) / (3 - 0.8) * 12.0, 0, 12)
        notes.append(f"P/B {pb:.2f}")
    if pe is None and pb is None:  # fall back to range position
        price, rng = fund.get("price"), fund.get("range_52w")
        if price and rng and "-" in str(rng):
            try:
                rlo, rhi = [float(x) for x in str(rng).split("-")]
                if rhi > rlo:
                    pos = (price - rlo) / (rhi - rlo)
                    val_s += _clamp((1 - pos) * 30.0, 0, 30)
            except ValueError:
                pass

    # --- Quality component (0..25): ROE, leverage, beta ---
    qual_s = 0.0
    roe = fund.get("roe")
    if isinstance(roe, (int, float)):
        qual_s += _clamp(roe / 20.0 * 12.0, 0, 12)   # 20% ROE -> full
        if roe >= 15:
            notes.append(f"ROE {roe:.0f}%")
    de = fund.get("debt_to_equity")
    if isinstance(de, (int, float)):
        qual_s += _clamp((150 - de) / 150 * 7.0, 0, 7)
    beta = fund.get("beta")
    if isinstance(beta, (int, float)):
        qual_s += 6.0 if beta <= 1.0 else 3.0
        if beta <= 1.0:
            notes.append("low beta")

    score = div_s + val_s + qual_s

    # --- Yield-trap penalty ---
    is_trap, trap_reasons = detect_yield_trap(fund, strat)
    if is_trap:
        score *= 0.5
        notes.append("⚠️ yield-trap risk")

    return _clamp(score), dy, notes


def technical_score(snap: dict, strat: dict) -> tuple[float, list[str]]:
    notes: list[str] = []
    score = 0.0
    close = snap.get("close")
    rsi = snap.get("rsi")
    trend = snap.get("trend", "—")
    rng_pos = snap.get("range_pos_pct")
    vol, vavg = snap.get("volume"), snap.get("vol_avg20")
    bb_lower = snap.get("bb_lower")

    # Trend (0..35): uptrend rewarded.
    if trend in ("Uptrend", "Above SMA"):
        score += 35.0
        notes.append("uptrend")
    elif trend in ("Downtrend", "Below SMA"):
        score += 8.0
        notes.append("downtrend")
    else:
        score += 18.0

    # RSI (0..30): best when oversold/normalizing, penalize overbought.
    if rsi is not None:
        if rsi < strat["rsi_oversold"]:
            score += 30.0
            notes.append(f"RSI {rsi:.0f} oversold")
        elif rsi < strat["rsi_overbought"]:
            # linear sweet spot, peak near oversold edge
            score += _clamp(30.0 * (strat["rsi_overbought"] - rsi) /
                            (strat["rsi_overbought"] - strat["rsi_oversold"]), 0, 30)
            notes.append(f"RSI {rsi:.0f}")
        else:
            score += 4.0
            notes.append(f"RSI {rsi:.0f} overbought")
    else:
        score += 12.0

    # Support proximity (0..20): near 52w low or below lower Bollinger = entry.
    if rng_pos is not None:
        score += _clamp((100 - rng_pos) / 100 * 20.0, 0, 20)
    if close and bb_lower and close <= bb_lower:
        score = min(100.0, score + 5.0)
        notes.append("below lower BB")

    # Volume confirmation (0..15).
    if vol and vavg and vavg > 0:
        ratio = vol / vavg
        score += _clamp((ratio - 0.8) / 1.2 * 15.0, 0, 15)
        if ratio >= 1.5:
            notes.append("high volume")

    return _clamp(score), notes


# ----------------------------- sizing -------------------------------------

def _position_size(entry: float, stop: float, strat: dict) -> tuple[int, float]:
    """Risk-based lots. Risk per trade caps loss to risk_per_trade_pct of
    portfolio at the stop; also capped by max_position_pct weight."""
    if not entry or entry <= 0:
        return 0, 0.0
    port = strat["portfolio_idr"]
    risk_idr = port * strat["risk_per_trade_pct"] / 100.0
    per_share_risk = max(entry - stop, entry * 0.01)
    shares_by_risk = risk_idr / per_share_risk
    shares_by_cap = (port * strat["max_position_pct"] / 100.0) / entry
    shares = min(shares_by_risk, shares_by_cap)
    lots = int(shares // LOT_SIZE)
    return max(lots, 0), lots * LOT_SIZE * entry


# ----------------------------- main entry ---------------------------------

def evaluate(symbol: str, cfg: dict, df_enriched: pd.DataFrame | None = None,
             fund: dict | None = None) -> Recommendation:
    strat = _strat(cfg)
    if df_enriched is None:
        df_enriched = indicators.enrich(db.load_prices(symbol), cfg)
    if fund is None:
        fund = db.load_fundamentals(symbol)

    if df_enriched is None or df_enriched.empty or len(df_enriched) < strat["min_history_days"]:
        return Recommendation(symbol, "SKIP", None, None, None, None, None, None,
                              "—", None, None, None, None, None, None,
                              "insufficient history")

    fund = fund or {}
    snap = indicators.snapshot(df_enriched, cfg)
    f_score, dy, f_notes = fundamental_score(fund, strat)
    is_trap, trap_reasons = detect_yield_trap(fund, strat)
    t_score, t_notes = technical_score(snap, strat)
    composite = (strat["weight_fundamental"] * f_score +
                 strat["weight_technical"] * t_score)

    close = snap.get("close")
    gate_passed = dy is not None and dy >= strat["min_yield_pct"]

    # Decide action.
    if not gate_passed:
        action = "SKIP" if dy is None else "HOLD"
        rationale = ("fails dividend gate; " +
                     "; ".join(f_notes[:2])) if dy is not None else "no dividend"
        entry = target = stop = None
        lots = None
        cost = None
    else:
        if composite >= strat["buy_threshold"]:
            action = "BUY"
        elif composite < strat["sell_threshold"]:
            action = "SELL"
        else:
            action = "HOLD"

        # Levels. Entry near support (min of close, lower BB if close above it).
        bb_lower = snap.get("bb_lower")
        entry = close
        if bb_lower and close and bb_lower < close:
            entry = round((close + bb_lower) / 2, 2)  # midway to support
        target = round(entry * (1 + strat["target_pct"] / 100), 2) if entry else None
        stop = round(entry * (1 - strat["stop_pct"] / 100), 2) if entry else None
        lots, cost = _position_size(entry, stop, strat) if action == "BUY" else (None, None)
        rationale = f"{action}: composite {composite:.0f}/100 · " + \
                    "; ".join((f_notes[:1] + t_notes[:2]))

    return Recommendation(
        symbol=symbol, action=action, composite=round(composite, 1),
        fundamental_score=round(f_score, 1), technical_score=round(t_score, 1),
        close=close, div_yield_pct=round(dy, 2) if dy is not None else None,
        rsi=round(snap["rsi"], 1) if snap.get("rsi") is not None else None,
        trend=snap.get("trend", "—"),
        range_pos_pct=round(snap["range_pos_pct"], 0) if snap.get("range_pos_pct") is not None else None,
        entry=entry, target=target, stop=stop, lots=lots,
        est_cost_idr=round(cost, 0) if cost else None, rationale=rationale,
        yield_trap=is_trap, trap_reasons="; ".join(trap_reasons),
        pe=_r(fund.get("pe")), pb=_r(fund.get("pb"), 2), roe=_r(fund.get("roe")),
        payout_ratio=_r(fund.get("payout_ratio")),
        earnings_growth=_r(fund.get("earnings_growth")),
        sector=fund.get("sector"),
        conviction=_conviction(action, f_score, t_score),
        ex_dividend_date=fund.get("ex_dividend_date"),
        days_to_cum=_days_to_cum(fund.get("ex_dividend_date")))


def _apply_sector_ranks(recs: list[Recommendation]) -> None:
    """Set sector_rank_pct = percentile of composite within each sector
    (100 = best scorer in its sector). Sharpens cross-sector comparison."""
    by_sector: dict[str, list[Recommendation]] = {}
    for r in recs:
        if r.composite is None or not r.sector:
            continue
        by_sector.setdefault(r.sector, []).append(r)
    for group in by_sector.values():
        n = len(group)
        if n == 1:
            group[0].sector_rank_pct = 100.0
            continue
        ordered = sorted(group, key=lambda r: r.composite)
        for i, r in enumerate(ordered):
            r.sector_rank_pct = round(i / (n - 1) * 100, 0)


def evaluate_universe(cfg: dict, symbols: list[str] | None = None) -> list[Recommendation]:
    if symbols is None:
        symbols = db.list_symbols(include_index=False)
    recs = [evaluate(s, cfg) for s in symbols]
    _apply_sector_ranks(recs)
    # Rank: BUY first by composite desc, then HOLD, then SELL, SKIP last.
    order = {"BUY": 0, "HOLD": 1, "SELL": 2, "SKIP": 3}
    recs.sort(key=lambda r: (order.get(r.action, 9), -(r.composite or -1)))
    return recs
