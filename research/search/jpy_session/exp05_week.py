"""Monday-long / Friday-short: longer holds, stop widths, trend filters, per pair."""
import numpy as np, pandas as pd
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms=["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]
rows=[]
for sym in syms:
    df=D.load(sym)
    for (side,wd) in [("long",0),("short",4),("long",4),("short",0)]:
        for hour in [0,1,2,3,4,5,6,8]:
            for sl_atr in [2.0,3.0,4.0]:
                for f,fk in [("none",{}),("d1ma50",dict(d1_ma=50)),("d1ma200",dict(d1_ma=200))]:
                    sides,dist=S.session_mask(df,hour=hour,side=side,weekdays=(wd,),sl_atr=sl_atr,**fk)
                    for hold in [12,18,23,30,36,47]:
                        if wd==4 and hour+hold>23: continue
                        sm=P.summarize(P.eval_r_fast(df,sides,dist,hold))
                        rows.append(dict(sym=sym,side=side,wd=wd,hour=hour,sl=sl_atr,f=f,hold=hold,**sm))
g=pd.DataFrame(rows); g.to_csv("research/search/jpy_session/grid_week.csv",index=False)
pd.set_option("display.width",250)
a=g.groupby(["side","wd","f","sl","hold"]).agg(mean_r=("mean_r","mean"),pos=("sum_r",lambda x:(x>0).mean())).reset_index()
for key,sub in a.groupby(["side","wd"]):
    print("\n",key); print(sub.pivot_table(index=["f","sl"],columns="hold",values="mean_r").round(3))
b=g[(g.side=="long")&(g.wd==0)&(g.f=="none")&(g.sl==3.0)].pivot_table(index="hour",columns=["hold"],values="mean_r").round(3)
print("\nMonday long sl3 none, mean over pairs by hour\n",b)
c=g[(g.side=="long")&(g.wd==0)&(g.f=="none")&(g.sl==3.0)&(g.hold==23)].pivot(index="hour",columns="sym",values="sum_r")
print("\nMonday long sl3 hold23 sum R by pair\n",c)
