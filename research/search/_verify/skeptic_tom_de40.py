import os, numpy as np, pandas as pd
from research.prop import harness as H
from research.search.jpy_session.strategies import build_index_turn_of_month as build, bdays_to_month_end
P=dict(hour=22,hold=72,sl_atr=3)
def run(split, sym="DE40", **p):
    df=H.load(sym,"H1",split=split); pp={**P,**p}
    sig=build(df,**pp); res=H.simulate(df,sig,risk=0.01); t=res["trades"]
    if split=="oos" and len(t): t=t[t.entry_time>=H.OOS_START]
    return df,sig,t
for split in ["is","oos"]:
    if split=="oos": os.environ["PROP_OOS"]="1"
    df,sig,t=run(split)
    tt=pd.DatetimeIndex(df.time); 
    lastwd=pd.Series(bdays_to_month_end(df)==0)
    months=pd.Series(tt.to_period("M")).nunique()
    has22=pd.Series((tt.hour==22)&(lastwd.values)).groupby(tt.to_period("M")).any()
    print(split,"months",months,"months w/ h22 bar on last weekday",has22.sum(),"signals",sum(s is not None for s in sig),"trades",len(t))
    print(" hours present on last weekdays:", sorted(set(tt.hour[lastwd.values])))
    if len(t):
        print(t[["entry_time","exit_time","profit","r","reason","bars"]].to_string())
        p=t.profit.sort_values(ascending=False)
        print(" net",round(t.profit.sum(),1),"top1",round(p.iloc[0],1),"top2",round(p.iloc[:2].sum(),1),"net ex top2",round(p.iloc[2:].sum(),1))
        print(" reasons",t.reason.value_counts().to_dict(), "meanR",round(t.r.mean(),3),"tstat",round(t.r.mean()/t.r.std()*np.sqrt(len(t)),2))
        yr=t.groupby(pd.DatetimeIndex(t.entry_time).year).profit.agg(['sum','count']); print(yr)
