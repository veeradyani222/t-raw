"""weekday x hour x hold x side grid, net of costs, all JPY pairs."""
import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms=sys.argv[1].split(",") if len(sys.argv)>1 else ["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]
tag=sys.argv[2] if len(sys.argv)>2 else "jpy"
rows=[]
for sym in syms:
    df=D.load(sym)
    for side in ["long","short"]:
        for hour in range(24):
            for wd in range(5):
                sides,dist=S.session_mask(df,hour=hour,side=side,weekdays=(wd,))
                for hold in [3,6,9,12,18,23]:
                    tr=P.eval_r_fast(df,sides,dist,hold)
                    sm=P.summarize(tr)
                    rows.append(dict(sym=sym,side=side,wd=wd,hour=hour,hold=hold,**sm))
g=pd.DataFrame(rows); g.to_csv(f"research/search/jpy_session/grid_wd_{tag}.csv",index=False)
a=g.groupby(["side","wd","hour","hold"]).agg(mean_r=("mean_r","mean"),pos_pairs=("sum_r",lambda x:(x>0).sum()),yrs=("yrs_pos","mean")).reset_index()
pd.set_option("display.width",250)
print(a.sort_values("mean_r",ascending=False).head(40).to_string())
for side in ["long","short"]:
  for wd in range(5):
    print(f"\n{side} wd={wd}"); print(a[(a.side==side)&(a.wd==wd)].pivot(index="hour",columns="hold",values="mean_r").round(2).T.to_string())
