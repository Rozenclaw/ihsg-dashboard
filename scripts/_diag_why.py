import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import explain
row = {"div_yield_pct": 7.65, "trend": "Uptrend", "rsi": 56,
       "range_pos_pct": 30, "composite": 73}
res = {
    "EN": explain.why_today(row, "EN"),
    "ID": explain.why_today(row, "ID"),
    "explain_file": explain.__file__,
}
import json
print(json.dumps(res, ensure_ascii=False, indent=2))
