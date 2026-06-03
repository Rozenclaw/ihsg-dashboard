#!/usr/bin/env python3
"""Offline test for Tier 2 & 3: dividend calendar, sector rank, conviction,
holdings import, news+sentiment, radar inputs. Synthetic data, no network."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db, fetch, strategy, divcal, portfolio, news  # noqa: E402
from src.config import get_config  # noqa: E402


def main() -> int:
    cfg = get_config()
    cfg["data"]["source"] = "synthetic"

    print("1) Seed data (ex-dividend dates + sectors) ...")
    fetch.refresh(full_universe=False, with_fundamentals=True, limit=25, verbose=False)
    f = db.load_fundamentals(db.list_symbols()[0])
    assert f.get("ex_dividend_date"), "no ex-dividend date stored"
    print(f"   -> ex-date {f['ex_dividend_date']}, sector {f['sector']}")

    print("2) Dividend calendar (cum-date math) ...")
    inf = divcal.info(f["ex_dividend_date"])
    assert inf["cum_date"] and inf["days_to_cum"] is not None, inf
    assert divcal.label(f["ex_dividend_date"], "ID") != "—"
    print(f"   -> cum {inf['cum_date']}, {inf['days_to_cum']}d, '{inf['status']}'")

    print("3) Strategy: sector rank + conviction + days_to_cum ...")
    recs = strategy.evaluate_universe(cfg)
    ranked = [r for r in recs if r.sector_rank_pct is not None]
    assert ranked, "no sector ranks computed"
    buys = [r for r in recs if r.action == "BUY"]
    convs = {r.conviction for r in buys}
    assert convs and convs <= {"high", "medium", "speculative"}, convs
    assert any(r.days_to_cum is not None for r in recs), "no days_to_cum"
    print(f"   -> {len(ranked)} ranked; BUY convictions={convs}; "
          f"sample rank={ranked[0].symbol}:{ranked[0].sector_rank_pct}%")

    print("4) Holdings import (CSV) + P/L + SELL flags ...")
    syms = db.list_symbols()[:3]
    csv = "symbol,lots,avg_price,note\n" + "\n".join(
        f"{s.replace('.JK','')},10,1000,test" for s in syms)
    n, errs = portfolio.import_csv(csv, replace=True)
    assert n == 3 and not errs, (n, errs)
    snap = portfolio.snapshot(cfg)
    assert len(snap["rows"]) == 3 and snap["cost"] > 0, snap
    assert abs((snap["value"] - snap["cost"]) - snap["pl"]) < 1.0
    print(f"   -> 3 holdings, value {snap['value']:,.0f}, P/L {snap['pl']:+,.0f} "
          f"({snap['pl_pct']:+.1f}%), SELL flags: {snap['sell_flags']}")
    db.delete_holding(syms[0])
    assert len(db.list_holdings()) == 2, "delete failed"
    print("   -> delete ok")

    print("5) News + rule-based sentiment ...")
    nd = news.get_news(syms[0])
    assert nd["items"], "no news items"
    assert nd["overall"] in ("positive", "negative", "neutral")
    print(f"   -> {len(nd['items'])} headlines, overall={nd['overall']} "
          f"(score {nd['overall_score']})")
    # sentiment scorer sanity
    from src.news import _score_title
    assert _score_title("profit surges to record high") > 0
    assert _score_title("shares plunge on fraud probe") < 0
    print("   -> sentiment scorer directionally correct")

    print("6) Bilingual cum-date label ...")
    print("   EN:", divcal.label(f["ex_dividend_date"], "EN"))
    print("   ID:", divcal.label(f["ex_dividend_date"], "ID"))

    print("\nALL TIER 2 & 3 TESTS PASSED ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
