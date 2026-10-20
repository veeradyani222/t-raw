import os
os.environ["PROP_OOS"] = "1"
import pandas as pd, numpy as np
from research.prop import harness as H
from research.search.gold_fix.strategies import build_gold_lowvol_donchian_fast as build
df = H.load("XAUUSD","H4",split="oos"); s=build(df)
idx=[i for i,e in enumerate(s) if e is not None and df.time[i]>=H.OOS_START]
stop=np.array([abs(df.close[i]-s[i].sl) for i in idx])
print("OOS signals",len(idx),"stop$ per 0.01lot: median",np.median(stop),"min",stop.min(),"max",stop.max(),
      "share >$74 (unaffordable at 0.75%)",np.mean(stop+0.31>74.3))
t=H.simulate(df,s,risk=0.0075)["trades"]; t=t[t.entry_time>=H.OOS_START]
print("lots",t.lots.value_counts().to_dict(),"risk_usd median",t.risk_usd.median() if "risk_usd" in t else None)
print("actual risk $ (lots*stop)", (t.lots*100*abs(t.entry-t.sl0)+t.lots*14).describe().round(1).to_dict())
dfi=H.load("XAUUSD","H4",split="is"); si=build(dfi)
ii=[i for i,e in enumerate(si) if e is not None]
st=np.array([abs(dfi.close[i]-si[i].sl) for i in ii]); print("IS signals",len(ii),"median stop",np.median(st),"share>$74",np.mean(st>74))
ti=H.simulate(dfi,si,risk=0.0075)["trades"]; print("IS lots",ti.lots.value_counts().head(8).to_dict())
