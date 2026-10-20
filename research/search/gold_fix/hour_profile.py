"""Descriptive: mean H1 bar return (in ATR units) by server hour, split 2015-19 vs 2020-23."""
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.gold_fix import lib as L
for sym in ["XAUUSD", "XAGUSD"]:
    df = H.load(sym, "H1", split="is")
    a = L.atr(df, 24)
    r = (df.close - df.open) / pd.Series(a).shift(1)
    t = df.time
    out = pd.DataFrame({"h": t.dt.hour, "p": np.where(t.dt.year < 2020, "A15-19", "B20-23"), "r": r})
    tab = out.groupby(["h", "p"]).r.agg(["mean", "count"]).unstack()
    tab["t_A"] = out[out.p=="A15-19"].groupby("h").r.apply(lambda v: v.mean()/v.std()*np.sqrt(len(v)))
    tab["t_B"] = out[out.p=="B20-23"].groupby("h").r.apply(lambda v: v.mean()/v.std()*np.sqrt(len(v)))
    print(sym); print(tab.round(3).to_string())
