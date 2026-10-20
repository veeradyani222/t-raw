import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.breakout import strategies as S
df = H.load("DE40","M30",split="oos")
P = {"rs":10,"re":10.5,"te":12.5,"exit_h":18,"sl_frac":0.75,"trend":"d","min_rng":0.1,"tp_r":None}
sigs = S.build_de40_xetra_orb(df, **P)
P2=dict(P); P2["trend"]=None
s2 = S.build_de40_xetra_orb(df, **P2)
t=pd.DatetimeIndex(df.time)
m=(t>=pd.Timestamp("2024-09-15"))&(t<pd.Timestamp("2025-01-10"))
print("sigs trend", sum(1 for i in np.where(m)[0] if sigs[i]), "no trend", sum(1 for i in np.where(m)[0] if s2[i]))
d=S._daily(df)
sub=pd.DataFrame({"time":t,"c":d["c"],"ema":d["ema"],"atr":d["atr"]})[m]
print(sub[t[m].hour==10].iloc[::5].to_string())
sm = df[m & (t.hour==10)][["time","open","high","low","close","spread"]]
print(sm.head(10).to_string())
for side in ("long","short"):
    tr=H.simulate(df,s2,risk=0.005)["trades"]
tr=tr[tr.entry_time>=pd.Timestamp("2024-01-01")]
print("no-trend OOS by side", tr.groupby("side").profit.agg(["count","sum"]).to_string(), "net", tr.profit.sum())
print("2026 no-trend", tr[tr.entry_time.dt.year==2026].profit.sum())
# exclude data-gap trade from trend version
tr1=H.simulate(df,sigs,risk=0.005)["trades"]; tr1=tr1[tr1.entry_time>=pd.Timestamp("2024-01-01")]
print("net excl gap trade", tr1[tr1.reason!="gap_sl"].profit.sum(), "if gap trade were -1R", tr1[tr1.reason!="gap_sl"].profit.sum()-50)
print("longs only net", tr1[tr1.side=="long"].profit.sum(), "shorts", tr1[tr1.side=="short"].profit.sum())
w=tr1[(tr1.entry_time>="2024-09-01")&(tr1.entry_time<"2025-01-31")]
print(w[["entry_time","exit_time","side","profit","reason"]].to_string())
idx=[i for i in np.where(m)[0] if sigs[i]]
print([(str(t[i]), sigs[i].side, sigs[i].sl, df.close[i]) for i in idx])
