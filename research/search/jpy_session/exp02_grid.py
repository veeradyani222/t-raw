"""Hour x hold x side grid on every JPY pair via the fast R prescreen."""
import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms = sys.argv[1].split(",") if len(sys.argv)>1 else ["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]
tag = sys.argv[2] if len(sys.argv)>2 else "jpy"
rows=[]
for sym in syms:
    df=D.load(sym)
    for side in ["long","short"]:
        for hour in range(24):
            sides,dist=S.session_mask(df,hour=hour,side=side,sl_atr=2.0)
            for hold in [2,4,6,9,12,15,18,23]:
                for cost in (True,False):
                    tr=P.eval_r_fast(df,sides,dist,hold,cost=cost)
                    sm=P.summarize(tr)
                    rows.append(dict(sym=sym,side=side,hour=hour,hold=hold,cost=cost,**sm))
g=pd.DataFrame(rows); g.to_csv(f"research/search/jpy_session/grid_{tag}.csv",index=False)
pd.set_option("display.width",250); pd.set_option("display.max_columns",30)
for side in ["long","short"]:
    for cost in (False,True):
        piv=g[(g.side==side)&(g.cost==cost)].pivot_table(index="hour",columns="hold",values="mean_r",aggfunc="mean").round(3)
        print(f"\n{side} cost={cost}: mean R/trade averaged over {syms}\n",piv)
gc=g[g.cost]
print(gc.sort_values("sum_r",ascending=False).head(30).to_string())
