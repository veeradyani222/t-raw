"""Session-timed entries in the D1 trend direction with multi-day holds."""
import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms=sys.argv[1].split(","); tag=sys.argv[2]
rows=[]
for sym in syms:
    df=D.load(sym)
    for d1 in [20,50,100]:
        for hour in [1,9]:
            for sl in [3.0,6.0]:
                sides,dist=S.session_mask(df,hour=hour,side="long",sl_atr=sl,d1_ma=d1,trend_mode="follow")
                for hold in [24,72,120]:
                    sm=P.summarize(P.eval_r(df,sides,dist,hold))
                    rows.append(dict(sym=sym,d1=d1,hour=hour,sl=sl,hold=hold,**sm))
    print(sym,flush=True)
g=pd.DataFrame(rows); g.to_csv(f"research/search/jpy_session/grid_trend_{tag}.csv",index=False)
pd.set_option("display.width",250)
print(g.pivot_table(index=["d1","hour","sl"],columns=["hold"],values="mean_r",aggfunc="mean").round(3))
print(g.sort_values("sum_r",ascending=False).head(25).to_string())
