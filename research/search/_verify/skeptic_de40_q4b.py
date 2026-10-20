import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.breakout import strategies as S
df = H.load("DE40","M30",split="oos")
t=pd.DatetimeIndex(df.time); hr=t.hour+t.minute/60
d=S._daily(df)
x=df.assign(day=t.normalize(),hr=hr,atr=d["atr"])
x=x[(x.time>="2024-10-01")&(x.time<"2024-10-20")]
for day,g in x.groupby("day"):
    r=g[g.hr==10]; w=g[(g.hr>=10.5)&(g.hr<12.5)]
    if len(r)==0: print(day,"no range bar"); continue
    print(day.date(), "rng", r.high.iloc[0]-r.low.iloc[0], "atr", round(r.atr.iloc[0],1), "maxc-rh", round(w.close.max()-r.high.iloc[0],1), "rl-minc", round(r.low.iloc[0]-w.close.min(),1))
