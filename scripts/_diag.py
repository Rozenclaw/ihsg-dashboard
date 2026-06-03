import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.datasources.synthetic_source import SyntheticSource
from src import db

f = SyntheticSource().fundamentals("BBRI.JK")
db.init_db()
db.save_fundamentals("BBRI.JK", f)
g = db.load_fundamentals("BBRI.JK")
result = {
    "gen_pe": f.get("pe"),
    "gen_ex": f.get("ex_dividend_date"),
    "stored_pe": g.get("pe"),
    "stored_ex": g.get("ex_dividend_date"),
    "stored_cols": sorted(g.keys()),
}
print(json.dumps(result, default=str, indent=2))
