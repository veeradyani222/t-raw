"""Skeptic analysis of gold_boll50 (read-only)."""
import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.trend.strategies import build_gold_boll50, build_bollinger_bo
P = {"n": 50, "k": 2, "sl_mult": 2}
for split in ("is", "oos"):
    df = H.load("XAUUSD", "H4", split=split)
    print("=====", split, df.time.iloc[0], df.time.iloc[-1], len(df), "score_from", df.attrs.get("score_from"))
    sigs = build_gold_boll50(df, **P)
    r = H.simulate(df, sigs, risk=0.005)
    t = r["trades"]
    if df.attrs.get("score_from") is not None:
        t = t[t.entry_time >= df.attrs["score_from"]]
    t = t.copy()
    print("trades", len(t), "net", round(t.profit.sum(),1), "win", round((t.profit>0).mean(),3), "avgR", round(t.r.mean(),3))
    print(t.groupby("side").profit.agg(["count","sum","mean"]).round(1))
    print("reasons", t.groupby("reason").profit.agg(["count","sum"]).round(1).to_dict())
    tp = t.sort_values("profit", ascending=False)
    tot = t.profit.sum()
    for k in (1,3,5,10):
        print(f"net without top {k}:", round(tot - tp.profit.head(k).sum(),1))
    print("top5", tp[["entry_time","side","profit","r","bars"]].head(5).to_string())
    t["hr"] = pd.DatetimeIndex(t.entry_time).hour
    print("by entry hour", t.groupby("hr").profit.agg(["count","sum"]).round(1).to_dict())
    t["yr"] = pd.DatetimeIndex(t.entry_time).year
    print("by year", t.groupby("yr").profit.agg(["count","sum"]).round(0).to_dict())
    # spread at entry bars
    sp = df["spread"].to_numpy(float) * 0.01 if "spread" in df else None
    if sp is not None:
        idx = pd.Index(df.time)
        hrs = pd.DatetimeIndex(df.time).hour
        print("median bar spread by hour", pd.Series(sp).groupby(hrs).median().round(3).to_dict())
    # buy and hold
    c = df.close.to_numpy(); f = df.attrs.get("score_from")
    c0 = df[df.time >= f].close.iloc[0] if f is not None else c[0]
    print("gold move", round(c0,1), "->", round(c[-1],1), f"{(c[-1]/c0-1)*100:.0f}%")
    # rollover penalty: extra 1.0 spread for entries at hour 0 bar closes
