"""Failure-pattern diagnostics: group trades (R multiples) by attributes."""
import sys
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.breakout import strategies as S

def diag(sym, tf, fn, **p):
    df = H.load(sym, tf, split="is")
    sig = getattr(S, fn)(df, **p)
    t = H.simulate(df, sig, risk=0.005)["trades"]
    dly = S._daily(df)
    idx = pd.Index(df.time).get_indexer(t.entry_time)
    t["hour"] = t.entry_time.dt.hour
    t["dow"] = t.entry_time.dt.dayofweek
    t["year"] = t.entry_time.dt.year
    up = (dly["c"] > dly["ema"])[idx]
    t["with_trend"] = np.where(t.side == "long", up, ~up)
    a = S.atr(df)[idx]
    t["stop_atr"] = (abs(t.entry - t.sl0) / dly["atr"][idx]).round(1)
    t["stopq"] = pd.qcut(t.stop_atr, 4, duplicates="drop")
    print(f"== {sym} {tf} {fn} {p}  n={len(t)}  meanR={t.r.mean():.3f}")
    for col in ("side", "hour", "dow", "year", "with_trend", "stopq", "reason"):
        g = t.groupby(col)["r"].agg(["count", "mean", "sum"]).round(3)
        print(g.T.to_string()); print()

if __name__ == "__main__":
    import ast
    diag(sys.argv[1], sys.argv[2], sys.argv[3], **ast.literal_eval(sys.argv[4] if len(sys.argv) > 4 else "{}"))
