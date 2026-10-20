"""Intraday momentum/reversal grid: from_hour x entry_hour x hold x mode."""
import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms=sys.argv[1].split(","); tag=sys.argv[2]
rows=[]
for sym in syms:
    df=D.load(sym)
    for fh in range(0,23):
        for eh in range(fh+1,24):
            if eh-fh>12: continue
            for mode in ["follow","fade"]:
                sides,dist=S.momentum_mask(df,fh,eh,mode)
                for hold in [1,2,4,8]:
                    sm=P.summarize(P.eval_r_fast(df,sides,dist,hold))
                    rows.append(dict(sym=sym,fh=fh,eh=eh,mode=mode,hold=hold,**sm))
    print(sym,flush=True)
g=pd.DataFrame(rows); g.to_csv(f"research/search/jpy_session/grid_mom_{tag}.csv",index=False)
a=g.groupby(["fh","eh","mode","hold"]).agg(mean_r=("mean_r","mean"),pos=("sum_r",lambda x:(x>0).sum()),yrs=("yrs_pos","mean"),n=("n","mean")).reset_index()
pd.set_option("display.width",250)
print(a.sort_values("mean_r",ascending=False).head(40).to_string())
print(g.sort_values("sum_r",ascending=False).head(30).to_string())
