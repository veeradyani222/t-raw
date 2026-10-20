import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from research.prop import harness as H
from research.search.trend.strategies import build_gold_boll50
df = H.load("XAUUSD","H4",split="oos"); s = build_gold_boll50(df, n=50, k=2, sl_mult=2)
sc = H.score(df, s, name="oos_full")
for r, m in sc["by_risk"].items():
    print(r, {k: (round(v,3) if isinstance(v,float) else v) for k, v in m.items() if k in ("net","avg_month","max_dd","worst_day","trades","safe","green_months","challenge_pass_rate")})
