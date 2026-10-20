"""Gotobi (5/10/15/20/25/month-end, rolled back to prior weekday) Tokyo-fix test."""
import numpy as np, pandas as pd
from research.search.jpy_session import data as D, strategies as S, prescreen as P

def gotobi_days(times):
    d = pd.DatetimeIndex(times).normalize().unique()
    out=set()
    for m in pd.period_range(d.min(), d.max(), freq="M"):
        for day in [5,10,15,20,25,None]:
            ts = m.to_timestamp(how="end").normalize() if day is None else pd.Timestamp(m.year,m.month,day)
            while ts.dayofweek>=5: ts -= pd.Timedelta(days=1)
            out.add(ts)
    return out
rows=[]
for sym in ["USDJPY","EURJPY","AUDJPY","GBPJPY","CHFJPY"]:
    df=D.load(sym); t=pd.DatetimeIndex(df.time); g=gotobi_days(t)
    isg=np.array([x in g for x in t.normalize()])
    for side in ["long","short"]:
      for hour in [23,0,1,2]:
        for hold in [1,2,3,4,6]:
          sides,dist=S.session_mask(df,hour=hour,side=side)
          for lab,m in [("gotobi",isg),("other",~isg)]:
            s2=sides.copy(); s2[~m]=None
            for cost in (True,False):
                sm=P.summarize(P.eval_r_fast(df,s2,dist,hold,cost=cost))
                rows.append(dict(sym=sym,side=side,hour=hour,hold=hold,days=lab,cost=cost,**sm))
g=pd.DataFrame(rows)
pd.set_option("display.width",250)
print(g[(~g.cost)].pivot_table(index=["side","hour","hold"],columns=["days","sym"],values="mean_r").round(3).to_string())
print(g[(g.cost)&(g.days=="gotobi")].pivot_table(index=["side","hour","hold"],columns=["sym"],values="mean_r").round(3).to_string())
