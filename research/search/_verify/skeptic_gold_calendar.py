import os, sys
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
os.environ["PROP_OOS"] = "1"
import pandas as pd, numpy as np
from research.prop import harness as H
from research.search.published_research.strategies import build_gold_calendar as build, build_pre_fomc, build_turn_of_month
P = {"tom_days_before": 0, "tom_hold": 4, "fomc_sl": 1.5}
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
od = H.load("XAUUSD", "H1", split="oos")
sigs = build(od, **P)
r = H.simulate(od, sigs, risk=0.02)
t = r["trades"]; t = t[t.entry_time >= "2024-01-01"]
print(t[["entry_time","exit_time","entry","exit","sl0","lots","profit","reason","bars"]].to_string())
print("n", len(t), "sum", t.profit.sum())
ps = t.profit.sort_values(ascending=False)
print("top1", ps.iloc[0], "top3", ps.iloc[:3].sum(), "top5", ps.iloc[:5].sum())
# signal count per month vs trades
sg = pd.Series([od.time.iloc[i] for i,e in enumerate(sigs) if e is not None])
sg = sg[sg >= "2024-01-01"]
print("signals", len(sg)); print(sg.dt.to_period("M").value_counts().sort_index().to_string())
# data coverage per month
tt = pd.DatetimeIndex(od.time); tt = tt[tt >= "2024-01-01"]
print(pd.Series(1, index=tt).resample("M").count().to_string())
