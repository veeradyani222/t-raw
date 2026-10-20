"""Average H1 return (in ATR14 units, gross) by weekday x hour; per year stability."""
import numpy as np, pandas as pd, sys
from research.search.jpy_session import data as D, strategies as S
syms=sys.argv[1].split(",")
prof=[]
for sym in syms:
    df=D.load(sym); t=pd.DatetimeIndex(df.time)
    a=S.atr_simple(df,14); c=df.close.to_numpy()
    r=np.r_[np.nan,np.diff(c)]/np.r_[np.nan,a[:-1]]   # bar return / ATR known before the bar
    prof.append(pd.DataFrame(dict(sym=sym,wd=t.dayofweek,hour=t.hour,yr=t.year,r=r)))
p=pd.concat(prof).dropna()
m=p.groupby(["wd","hour"]).r.mean().unstack(0)
pd.set_option("display.width",250)
print("mean bar return/ATR x100, by hour (rows) and weekday (cols)\n",(m*100).round(1).to_string())
cum=m.T.stack().cumsum()
print("\ncumulative week path (ATR units)\n",cum.round(2).unstack(1).T.to_string())
# yearly stability of Monday 0-23 and Friday
for wd in range(5):
    y=p[p.wd==wd].groupby("yr").r.sum()/len(syms)
    print(wd,(y).round(1).to_dict())
