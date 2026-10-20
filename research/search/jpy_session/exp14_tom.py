import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms=sys.argv[1].split(",")
rows=[]
for sym in syms:
    df=D.load(sym)
    n=S.bdays_to_month_end(df); hr,_=S._hours(df); a=S.atr_simple(df,14)
    for side in ["long","short"]:
      for k in [0,1,2,3]:
        for hour in [15,20,22]:
            for sl in [3.0,5.0]:
                ok=(hr==hour)&(n==k)&np.isfinite(a)
                sides=np.full(len(df),None,dtype=object); sides[ok]=side
                for hold in [24,48,72,96]:
                    sm=P.summarize(P.eval_r(df,sides,sl*a,hold))
                    rows.append(dict(sym=sym,side=side,k=k,hour=hour,sl=sl,hold=hold,**sm))
g=pd.DataFrame(rows)
pd.set_option("display.width",250)
for side in ["long","short"]:
    print(side); print(g[g.side==side].pivot_table(index=["k","hour","sl"],columns=["sym","hold"],values="mean_r").round(2).to_string())
print(g.sort_values("sum_r",ascending=False).head(20).to_string())
