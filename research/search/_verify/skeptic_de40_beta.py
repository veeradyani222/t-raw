import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.breakout import strategies as S
for split in ("is","oos"):
    df = H.load("DE40","M30",split=split)
    t=pd.DatetimeIndex(df.time); hr=t.hour+t.minute/60
    if split=="oos":
        keep=(t>=pd.Timestamp("2024-01-01"))&~((t>=pd.Timestamp("2024-10-01"))&(t<pd.Timestamp("2025-02-01")))
    else: keep=np.ones(len(df),bool)
    x=df[keep].assign(day=t[keep].normalize(),hr=hr[keep])
    a=x[x.hr==10.5].set_index("day").close; b=x[x.hr==18].set_index("day").close
    j=pd.concat([a,b],axis=1,keys=["a","b"]).dropna()
    print(split,"days",len(j),"mean 10:30->18:30 pts", round((j.b-j.a).mean(),2), "t", round((j.b-j.a).mean()/(j.b-j.a).std()*np.sqrt(len(j)),2))
    P = {"rs":10,"re":10.5,"te":12.5,"exit_h":18,"sl_frac":0.75,"trend":"d","min_rng":0.1,"tp_r":None}
    tr=H.simulate(df,S.build_de40_xetra_orb(df,**P),risk=0.005)["trades"]
    if split=="oos": tr=tr[(tr.entry_time>="2024-01-01")&(tr.reason!="gap_sl")]
    tr["pts"]=np.where(tr.side=="long",tr.exit-tr.entry,tr.entry-tr.exit)
    print("  strat mean pts/trade by side", tr.groupby("side").pts.mean().round(2).to_dict(), "mean R", tr.r.mean().round(3), "tstat R", round(tr.r.mean()/tr.r.std()*np.sqrt(len(tr)),2))
