import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.indicator_screen import strategies as S
for split in ("is","oos"):
    df = H.load("US500","D1",split=split)
    c=df.close; ma=c.rolling(200).mean()
    lg=(c>ma).fillna(False).to_numpy(); sh=np.zeros(len(df),bool)
    sig=S.events_to_entries(df,lg,sh,trend=False)
    tr=H.simulate(df,sig,risk=0.015)["trades"]
    sf=df.attrs.get("score_from")
    if sf is not None: tr=tr[tr.entry_time>=sf]
    print(split,"baseline every-bar long above SMA200: trades",len(tr),"net",round(tr.profit.sum()),"per trade",round(tr.profit.mean(),1),"win",round((tr.profit>0).mean(),3))
    sq=S.build_index_d1_squeeze(df); tr2=H.simulate(df,sq,risk=0.015)["trades"]
    if sf is not None: tr2=tr2[tr2.entry_time>=sf]
    print(split,"squeeze: trades",len(tr2),"per trade",round(tr2.profit.mean(),1),"win",round((tr2.profit>0).mean(),3))
