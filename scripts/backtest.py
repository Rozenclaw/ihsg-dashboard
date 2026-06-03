#!/usr/bin/env python3
"""CLI: run the strategy backtest and print metrics vs IHSG.

Examples:
  python scripts/backtest.py
  python scripts/backtest.py --lookback 252 --rebalance 5 --max-positions 8
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import backtest  # noqa: E402
from src.config import get_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback", type=int, default=504, help="trading days")
    ap.add_argument("--rebalance", type=int, default=5, help="rebalance every N days")
    ap.add_argument("--max-positions", type=int, default=10)
    args = ap.parse_args()

    res = backtest.run(get_config(), lookback_days=args.lookback,
                       rebalance_every=args.rebalance, max_positions=args.max_positions)
    if "error" in res:
        print("Backtest error:", res["error"])
        return

    print("=== Backtest results ===")
    print(f"Window (days):        {res['days']}")
    print(f"Start equity:         {res['start_equity']:,.0f} IDR")
    print(f"End equity:           {res['end_equity']:,.0f} IDR")
    print(f"Total return:         {res['total_return_pct']:+.1f}%")
    print(f"CAGR:                 {res['cagr_pct']:+.1f}%")
    print(f"Max drawdown:         {res['max_drawdown_pct']:.1f}%")
    print(f"Sharpe (daily->ann):  {res['sharpe']:.2f}")
    if res["benchmark_return_pct"] is not None:
        print(f"IHSG buy&hold:        {res['benchmark_return_pct']:+.1f}%  "
              f"(strategy {'beat' if res['total_return_pct'] > res['benchmark_return_pct'] else 'lagged'} benchmark)")
    print(f"Open positions (end): {res['open_positions_end']}")
    print("\n⚠️ Indicative only (fundamentals not point-in-time). Not financial advice.")


if __name__ == "__main__":
    main()
