import os, pandas as pd
os.environ["PROP_OOS"]="1"
from research.prop import harness as H
from research.search.jpy_session.strategies import bdays_to_month_end
for split in ["is","oos"]:
    df=H.load("DE40","H1",split=split); t=pd.DatetimeIndex(df.time)
    lw=bdays_to_month_end(df)==0
    d=pd.DataFrame({"m":t.to_period("M"),"wd":t.dayofweek,"h":t.hour})[lw]
    g=d.groupby("m").agg(wd=("wd","first"),maxh=("h","max"))
    miss=g[g.maxh<22]; print(split, "missing months", len(miss), "of", len(g)); print(miss.wd.value_counts().to_dict())
    fri=d[d.wd==4].groupby("m").h.max(); print(" friday last-weekday maxhour counts", fri.value_counts().to_dict())
