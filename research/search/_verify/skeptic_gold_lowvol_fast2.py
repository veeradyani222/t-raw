import os
os.environ["PROP_OOS"] = "1"
import pandas as pd
from research.prop import harness as H
from research.search.gold_fix.strategies import build_gold_lowvol_donchian_fast as build
from research.search.gold_fix.ideas import build_donchian
df = H.load("XAUUSD","H4",split="oos")
for nm,s in [("raw",build_donchian(df,n_entry=15,n_exit=5,atr_stop=2,trail_atr=4)),
             ("cand",build(df))]:
    for r in (0.0025,0.005,0.0075):
        print(H.summary_line(H.score(df,s,risks=(r,),name=f"{nm}@{r}")))
t=H.simulate(df,build(df),risk=0.0075)["trades"]; t=t[t.entry_time>=H.OOS_START]
print("exit hours", pd.DatetimeIndex(t.exit_time).hour.value_counts().sort_index().to_dict())
t["y"]=pd.DatetimeIndex(t.entry_time).year; print(t.groupby("y").profit.agg(["sum","count"]))
