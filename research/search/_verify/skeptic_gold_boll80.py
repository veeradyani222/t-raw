import os, sys, json
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.trend import strategies as S
R=0.0125
o = H.load("XAUUSD","H4",split="oos")
sigs = S.build_gold_boll80(o, n=80,k=2.5,sl_mult=3)
res = H.simulate(o, sigs, risk=R)
t = res["trades"]; t = t[t.entry_time>=H.OOS_START]
print("OOS trades", len(t), "net", round(t.profit.sum(),1), "win", round((t.profit>0).mean(),3))
tp = t.sort_values("profit", ascending=False)
print(tp[["entry_time","exit_time","side","profit","r","reason","bars"]].head(8).to_string())
print("top1 share", tp.profit.iloc[0]/t.profit.sum(), "top3", tp.profit.iloc[:3].sum()/t.profit.sum(), "net ex top2", t.profit.sum()-tp.profit.iloc[:2].sum())
print("by side", t.groupby("side").profit.agg(["count","sum"]).to_dict())
print("reasons", t.groupby("reason").profit.agg(["count","sum"]).to_dict())
# R stats bootstrap
r = t.r.to_numpy(); print("mean R", r.mean(), "t-stat", r.mean()/r.std(ddof=1)*np.sqrt(len(r)))
# exposure / buy-hold
c=o.close.to_numpy(); m=o.time>=H.OOS_START
print("gold OOS move", c[m.to_numpy()][0], "->", c[-1])
# in-sample R stats
i = H.load("XAUUSD","H4",split="is")
ti = H.simulate(i, S.build_gold_boll80(i,n=80,k=2.5,sl_mult=3), risk=R)["trades"]
print("IS trades", len(ti), "meanR", ti.r.mean(), "t", ti.r.mean()/ti.r.std()*np.sqrt(len(ti)), "IS top3 share", ti.profit.nlargest(3).sum()/ti.profit.sum())
# neighbours OOS
rows=[]
for n in (50,80,120):
  for k in (1.5,2.0,2.5):
    for sl in (2,3):
      s=H.score(o, S.build_bollinger_bo(o,n=n,k=k,sl_mult=sl), risks=(R,))
      h=s["headline"]; rows.append((n,k,sl,round(h["net"]),round(h["max_dd"]),h["trades"]))
for x in rows: print("nbr",x)
for lab,kw in (("long",dict(long_only=True)),("short",dict(short_only=True))):
  h=H.score(o,S.build_gold_boll80(o,n=80,k=2.5,sl_mult=3,**kw),risks=(R,))["headline"]; print(lab,round(h["net"]),h["trades"])
# random-entry null: same exit engine, random onsets at same frequency, OOS
rng=np.random.default_rng(1); nets=[]
nb=len(o); ntr=int((np.array([e is not None for e in sigs])).sum())
for rep in range(40):
  lo=np.zeros(nb,bool); sh=np.zeros(nb,bool)
  idx=rng.choice(np.arange(300,nb),ntr,replace=False); side=rng.random(ntr)<0.5
  lo[idx[side]]=True; sh[idx[~side]]=True
  cc=o.close.to_numpy(); mm=pd.Series(cc).rolling(80).mean().to_numpy()
  ss=S._emit(o,lo,sh,sl_mult=3,exit_long=cc<mm,exit_short=cc>mm,mode="state")
  nets.append(H.score(o,ss,risks=(R,))["headline"]["net"])
nets=np.array(nets); print("random null OOS net: mean",nets.mean(),"pctile of 793:",(nets<793).mean(), "p90",np.percentile(nets,90))
# other grid-1 gold H4 rules OOS
for nm,f in (("ma",S.build_ma_cross),("donch",S.build_donchian),("st",S.build_supertrend),("kelt",S.build_keltner_bo),("macd",S.build_macd),("psar",S.build_psar),("tsmom",S.build_tsmom)):
  try:
    h=H.score(o,f(o),risks=(R,))["headline"]; print("rule",nm,round(h["net"]),round(h["max_dd"]),h["trades"])
  except Exception as e: print(nm,e)
