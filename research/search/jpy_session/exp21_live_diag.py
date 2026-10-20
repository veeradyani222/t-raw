"""Why the live CHFJPY rule loses in-sample: by year, gross vs cost, vs trend."""
import numpy as np, pandas as pd
from research.search.jpy_session import data as D, strategies as S, prescreen as P
for sym in ["CHFJPY","AUDJPY","EURJPY"]:
    df=D.load(sym); sides,dist=S.session_mask(df,hour=0,side="long")
    tr=P.eval_r_fast(df,sides,dist,12); g=P.eval_r_fast(df,sides,dist,12,cost=False)
    tr["gross"]=g.r.values; tr["cost"]=tr.gross-tr.r
    m=df.set_index("time").close.resample("ME").last()
    mret=m.pct_change()
    tr["m"]=tr.time.dt.to_period("M")
    mm=tr.groupby("m").agg(net=("r","sum"),gross=("gross","sum"))
    mm["pair_ret"]=mret.to_period("M").reindex(mm.index).values
    print(sym, "yearly:"); print(tr.groupby(tr.time.dt.year).agg(n=("r","size"),net=("r","sum"),gross=("gross","sum"),cost=("cost","mean")).round(2).T.to_string())
    print(" corr(monthly net R, pair monthly return)=%.2f"%mm.net.corr(mm.pair_ret))
    q=pd.qcut(mm.pair_ret,3,labels=["pair down","flat","pair up"])
    print(mm.groupby(q).net.mean().round(2).to_dict())
    tr["sp"]=df.spread.to_numpy()[np.searchsorted(df.time.to_numpy(),tr.time.to_numpy())]
    print(" net R by entry-bar spread tercile", tr.groupby(pd.qcut(tr.sp,3,duplicates="drop")).r.mean().round(3).to_dict())
