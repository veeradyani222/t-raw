import numpy as np, pandas as pd
from research.search.jpy_session import data as D, strategies as S, prescreen as P
rows=[]
for sym in ["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]:
    df=D.load(sym); n=S.bdays_to_month_end(df); hr,_=S._hours(df); a=S.atr_simple(df,14)
    for k in [0,1,2]:
      for hour in [3,9,15,21]:
        ok=(hr==hour)&(n==k)&np.isfinite(a)
        for side in ["long","short"]:
          sides=np.full(len(df),None,dtype=object); sides[ok]=side
          for hold in [24,48,96]:
            sm=P.summarize(P.eval_r(df,sides,3.0*a,hold))
            rows.append(dict(sym=sym,k=k,hour=hour,side=side,hold=hold,**sm))
g=pd.DataFrame(rows); pd.set_option("display.width",250)
print(g.pivot_table(index=["side","k","hour"],columns="hold",values="mean_r",aggfunc="mean").round(2).to_string())
print(g[(g.side=="short")&(g.k==1)&(g.hold==48)].pivot(index="hour",columns="sym",values="mean_r").round(2))
