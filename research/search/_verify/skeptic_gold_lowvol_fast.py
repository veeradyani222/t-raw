import os, itertools
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.gold_fix.strategies import build_gold_lowvol_donchian_fast as build
from research.search.gold_fix.ideas import build_donchian
P = {"n_entry":15,"n_exit":5,"atr_stop":2,"trail_atr":4,"atrp_max":0.5,"atrp_window":500,"adx_min":20}
R=0.0075
df = H.load("XAUUSD","H4",split="oos")
sigs = build(df, **P)
res = H.simulate(df, sigs, risk=R)
t = res["trades"]; t = t[t.entry_time >= H.OOS_START]
print("n",len(t)); print(t[["entry_time","exit_time","side","r","profit","reason","bars"]].to_string())
p = t.profit.sort_values(ascending=False)
print("net",t.profit.sum(),"top1",p.iloc[0],"top2",p.iloc[:2].sum(),"top3",p.iloc[:3].sum(), "net ex top2", p.iloc[2:].sum())
print("by side", t.groupby("side").profit.agg(["sum","count"]))
print("by reason", t.groupby("reason").profit.agg(["sum","count"]))
# bootstrap mean r
rng=np.random.default_rng(0); r=t.r.values
bs=[rng.choice(r,len(r)).mean() for _ in range(5000)]
print("mean R",r.mean(),"P(mean<=0)",np.mean(np.array(bs)<=0))
# entry hours
print("entry hours", pd.DatetimeIndex(t.entry_time).hour.value_counts().sort_index().to_dict())
# unfiltered baseline OOS
for nm,s in [("raw donch 15/5 trail4", build_donchian(df,n_entry=15,n_exit=5,atr_stop=2,trail_atr=4)),
             ("raw donch 20/10", build_donchian(df,n_entry=20,n_exit=10))]:
    sc=H.score(df,s,risks=(R,),name=nm); print(H.summary_line(sc))
# neighbour grid OOS
rows=[]
for ne,nx,tr,am,ad in itertools.product([15,20],[5,7,10],[4,5],[0.4,0.5,0.6],[15,20,25]):
    s=build(df,n_entry=ne,n_exit=nx,atr_stop=2,trail_atr=tr,atrp_max=am,atrp_window=500,adx_min=ad)
    sc=H.simulate(df,s,risk=R)["trades"]; sc=sc[sc.entry_time>=H.OOS_START]
    rows.append((ne,nx,tr,am,ad,len(sc),round(sc.profit.sum())))
g=pd.DataFrame(rows,columns="ne nx tr am ad n net".split())
print(g.to_string()); print("grid positive frac",(g.net>0).mean(),"median",g.net.median())
# gold move OOS
d=df[df.time>=H.OOS_START]; print("gold",d.close.iloc[0],d.close.iloc[-1])
