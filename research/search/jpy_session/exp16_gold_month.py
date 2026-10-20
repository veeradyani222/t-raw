"""Gold position-in-month profile: k = business days left (0..22) x side x hold."""
import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S, prescreen as P
sym=sys.argv[1]; hour=int(sys.argv[2]) if len(sys.argv)>2 else 15
df=D.load(sym); n=S.bdays_to_month_end(df); hr,_=S._hours(df); a=S.atr_simple(df,14)
t=pd.DatetimeIndex(df.time)
# days INTO the month too (business days elapsed before this date)
first=t.normalize().to_period("M").to_timestamp()
into=np.array([np.busday_count(f.date(),d.date()) for f,d in zip(first,t.normalize())])
rows=[]
for lab,arr in [("left",n),("into",into)]:
  for k in range(0,8):
    ok=(hr==hour)&(arr==k)&np.isfinite(a)
    for side in ["long","short"]:
        sides=np.full(len(df),None,dtype=object); sides[ok]=side
        for hold in [24,48,96]:
            tr=P.eval_r(df,sides,3.0*a,hold); sm=P.summarize(tr)
            rows.append(dict(cnt=lab,k=k,side=side,hold=hold,**sm))
g=pd.DataFrame(rows); pd.set_option("display.width",250)
print(g.pivot_table(index=["cnt","k"],columns=["side","hold"],values="mean_r").round(2).to_string())
print(g.pivot_table(index=["cnt","k"],columns=["side","hold"],values="yrs_pos").to_string())
