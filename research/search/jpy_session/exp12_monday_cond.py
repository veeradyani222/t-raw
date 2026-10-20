"""What separates good and bad Monday-long trades? (features known at entry)"""
import numpy as np, pandas as pd
from research.search.jpy_session import data as D, strategies as S, prescreen as P
syms=["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]
allt=[]
for sym in syms:
    df=D.load(sym); t=pd.DatetimeIndex(df.time); c=df.close.to_numpy(); o=df.open.to_numpy()
    a=S.atr_simple(df,14)
    sides,dist=S.session_mask(df,hour=0,side="long",weekdays=(0,))
    tr=P.eval_r(df,sides,dist,36)
    idx=np.searchsorted(df.time.to_numpy(),tr.time.to_numpy())
    gap=(o[idx]-c[idx-1])/a[idx]
    bar0=(c[idx]-o[idx])/a[idx]
    wk=(c[idx-1]-c[np.maximum(idx-120,0)])/a[idx]    # last ~week (120 bars) into Friday close
    fri=(c[idx-1]-c[np.maximum(idx-24,0)])/a[idx]
    d1=S.daily_prior(df,50)[idx]
    volr=(a/S.sma(a,500))[idx]
    allt.append(tr.assign(sym=sym,gap=gap,bar0=bar0,wk=wk,fri=fri,d1=d1,volr=volr))
T=pd.concat(allt)
for f in ["gap","bar0","wk","fri","volr"]:
    T["q"]=T.groupby("sym")[f].transform(lambda x: pd.qcut(x,4,labels=False,duplicates="drop"))
    print(f, T.groupby("q").r.agg(["mean","count"]).round(3).T.to_string())
print("d1", T.groupby("d1").r.agg(["mean","count"]).round(3).T.to_string())
print("year", T.groupby(T.time.dt.year).r.agg(["mean","sum"]).round(2).T.to_string())
