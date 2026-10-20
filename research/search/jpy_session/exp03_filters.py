"""Hour-0 long: does any causal filter lift the gross edge above costs?"""
import numpy as np, pandas as pd
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms=["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]
F={"none":{},"d1ma20":dict(d1_ma=20),"d1ma50":dict(d1_ma=50),"d1ma100":dict(d1_ma=100),"d1ma200":dict(d1_ma=200),
   "d1mom20":dict(d1_ma=20,d1_kind="mom"),"d1mom60":dict(d1_ma=60,d1_kind="mom"),
   "h1ma200":dict(ma_n=200),"h1ma500":dict(ma_n=500),
   "vol_lo":dict(vol_hi=0.9),"vol_hi":dict(vol_lo=1.1),"no_mon":dict(weekdays=(1,2,3,4)),
   "mon":dict(weekdays=(0,)),"tue":dict(weekdays=(1,)),"wed":dict(weekdays=(2,)),"thu":dict(weekdays=(3,)),"fri":dict(weekdays=(4,))}
rows=[]
for sym in syms:
    df=D.load(sym)
    for fn,f in F.items():
        for side in ["long","short"]:
            sides,dist=S.session_mask(df,hour=0,side=side,**f)
            for cost in (True,False):
                sm=P.summarize(P.eval_r_fast(df,sides,dist,12,cost=cost))
                rows.append(dict(sym=sym,f=fn,side=side,cost=cost,**sm))
g=pd.DataFrame(rows)
pd.set_option("display.width",250)
for side in ["long","short"]:
  for cost in (False,True):
    print(f"\n{side} cost={cost} mean R/trade (hour0 hold12)")
    print(g[(g.side==side)&(g.cost==cost)].pivot(index="f",columns="sym",values="mean_r").round(3).assign(avg=lambda x:x.mean(1).round(3)))
print(g[(g.side=="long")&(g.cost)].pivot(index="f",columns="sym",values="n"))
