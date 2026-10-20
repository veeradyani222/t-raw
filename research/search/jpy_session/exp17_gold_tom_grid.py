import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S, prescreen as P
rows=[]
for sym in sys.argv[1].split(","):
    df=D.load(sym); n=S.bdays_to_month_end(df); hr,_=S._hours(df); a=S.atr_simple(df,14)
    for k in [0,1]:
      for hour in range(2,23,2):
        ok=(hr==hour)&(n==k)&np.isfinite(a)
        sides=np.full(len(df),None,dtype=object); sides[ok]="long"
        for sl in [2.0,3.0,4.0]:
          for hold in [24,48,72,96,120]:
            tr=P.eval_r(df,sides,sl*a,hold); sm=P.summarize(tr)
            rows.append(dict(sym=sym,k=k,hour=hour,sl=sl,hold=hold,**sm))
g=pd.DataFrame(rows); pd.set_option("display.width",250)
print(g[g.sl==3.0].pivot_table(index=["sym","k","hour"],columns="hold",values="mean_r").round(2).to_string())
print(g[g.k==0].pivot_table(index=["sym","sl"],columns="hold",values="mean_r").round(2).to_string())
print(g[(g.sl==3.0)].pivot_table(index=["sym","k","hour"],columns="hold",values="yrs_pos").to_string())
