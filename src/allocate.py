"""Monthly stacking allocator (DCA budget splitter).

Given a monthly budget (IDR) and the day's BUY recommendations, decide how many
whole IDX lots (100 shares) to buy of each pick so the total stays within budget.

Approach:
  1. Take the top-N BUY picks (uptrend-first, then composite score).
  2. Target weights proportional to composite score (better pick -> bigger slice).
  3. Greedily buy whole lots, each time adding the lot that best moves a holding
     toward its target weight, while it still fits the remaining cash.
  4. Report per-stock lots/shares/cost/% and any leftover cash.

Lot-aware and budget-safe: never exceeds the budget; leftover (too small for
even one lot of anything) is reported so you can carry it to next month.

NOT financial advice — a sizing helper for your own decisions.
"""
from __future__ import annotations

import pandas as pd

from . import strategy

LOT = strategy.LOT_SIZE  # 100 shares per lot on IDX


def _price(rec_row: dict) -> float | None:
    # prefer the model entry (near support); fall back to last close
    p = rec_row.get("entry") or rec_row.get("close")
    return float(p) if p else None


def plan(budget_idr: float, recs_df: pd.DataFrame, max_names: int = 3,
         use_entry: bool = True) -> dict:
    """Build a monthly stacking plan.

    recs_df: DataFrame of Recommendation rows (must include action, symbol,
             composite, trend, entry, close).
    Returns {rows, spent, leftover, budget, picks, note}.
    """
    if recs_df is None or recs_df.empty:
        return _empty(budget_idr, "no recommendations available")
    buys = recs_df[recs_df["action"] == "BUY"].copy()
    if buys.empty:
        return _empty(budget_idr, "no BUY signals today — consider holding cash "
                                  "or waiting for the next dip")

    # rank: uptrend first, then composite
    buys["_up"] = buys["trend"].isin(["Uptrend", "Above SMA"]).astype(int)
    buys = buys.sort_values(["_up", "composite"], ascending=[False, False]).head(max_names)

    # build candidate list with price + target weight
    cands = []
    wsum = 0.0
    for _, r in buys.iterrows():
        d = r.to_dict()
        px = _price(d) if use_entry else (float(d.get("close")) if d.get("close") else None)
        if not px or px <= 0:
            continue
        lot_cost = px * LOT
        if lot_cost > budget_idr:
            continue  # one lot already exceeds the whole budget
        w = max(float(d.get("composite") or 1), 1.0)
        wsum += w
        cands.append({"symbol": d["symbol"], "price": px, "lot_cost": lot_cost,
                      "weight": w, "composite": d.get("composite"),
                      "div_yield_pct": d.get("div_yield_pct"),
                      "lots": 0, "shares": 0, "cost": 0.0})
    if not cands:
        return _empty(budget_idr, "cheapest pick's 1 lot exceeds the budget — "
                                  "increase budget or pick lower-priced stocks")
    for c in cands:
        c["target_w"] = c["weight"] / wsum

    # greedy lot allocation toward target weights
    remaining = float(budget_idr)
    spent = 0.0
    progressed = True
    while progressed:
        progressed = False
        # consider buying one more lot of the name most under its target weight
        best = None
        best_gap = -1e9
        for c in cands:
            if c["lot_cost"] > remaining:
                continue
            cur_w = (c["cost"]) / spent if spent > 0 else 0.0
            gap = c["target_w"] - cur_w  # how under-allocated it is
            if gap > best_gap:
                best_gap = gap
                best = c
        if best is not None:
            best["lots"] += 1
            best["shares"] += LOT
            best["cost"] += best["lot_cost"]
            remaining -= best["lot_cost"]
            spent += best["lot_cost"]
            progressed = True

    rows = [c for c in cands if c["lots"] > 0]
    for c in rows:
        c["pct"] = (c["cost"] / spent * 100) if spent else 0.0
    rows.sort(key=lambda c: -c["cost"])

    note = ""
    if not rows:
        note = "budget too small for even one lot — try fewer names or higher budget"
    elif remaining >= min(c["lot_cost"] for c in cands):
        note = "some cash left that could buy another lot but would skew weights"

    return {"rows": rows, "spent": round(spent, 0), "leftover": round(remaining, 0),
            "budget": float(budget_idr), "picks": len(rows), "note": note}


def _empty(budget, note):
    return {"rows": [], "spent": 0.0, "leftover": float(budget),
            "budget": float(budget), "picks": 0, "note": note}
