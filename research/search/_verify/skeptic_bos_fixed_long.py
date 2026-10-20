import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.gold_fix.strategies import build_bos_fixed_long as build, build_bos
P = dict(atrp_min=0.6, tp_min_r=2, htf=["1D", 100])
for split in ("is", "oos"):
    df = H.load("XAUUSD", "M30", split=split)
    print("==", split, df.time.iloc[0], df.time.iloc[-1], len(df), "close first/last", df.close.iloc[0], df.close.iloc[-1])
    sigs = build(df, **P)
    res = H.simulate(df, sigs, risk=0.005)
    t = res["trades"]
    if split == "oos": t = t[t.entry_time >= H.OOS_START]
    print("trades", len(t), "net", round(t.profit.sum(), 1), "win", round((t.profit > 0).mean(), 3))
    print(t.reason.value_counts().to_dict())
    p = t.profit.sort_values(ascending=False)
    print("top1/top3/top5 share of net:", [round(p.head(k).sum() / t.profit.sum(), 2) for k in (1, 3, 5)])
    print("net excl top5:", round(p.iloc[5:].sum(), 1), " excl top10:", round(p.iloc[10:].sum(), 1))
    print("R stats: mean", round(t.r.mean(), 3), "median tgt_r", round(t.tgt_r.median(), 2), "stop_atr median", round(t.stop_atr.median(), 2), "min", round(t.stop_atr.min(), 3))
    stop_d = (t.entry - t.sl0)
    print("stop $ dist: min", round(stop_d.min(), 2), "p10", round(stop_d.quantile(.1), 2), "median", round(stop_d.median(), 2), " lots max", t.lots.max())
    print("by hour:", t.groupby("hour").profit.agg(['count','sum']).round(0).T.to_dict())
    print("by year:", t.groupby(t.entry_time.dt.year).profit.agg(['count','sum']).round(0).to_dict())
    # bootstrap: sign of mean
    rng = np.random.default_rng(0)
    bs = [rng.choice(t.profit.values, len(t)).mean() for _ in range(5000)]
    print("bootstrap P(mean<=0):", round(np.mean(np.array(bs) <= 0), 3))
    # null: random longs with same structure stop/tp mechanics -> drop all filters except side long, random subset same count
    allsig = build_bos(df, sides=("long",), tp_min_r=2.0, use_cmf=False, trend_ma=None)
    idx = [i for i, e in enumerate(allsig) if e is not None]
    print("unfiltered BOS-long candidates:", len(idx))
    nets = []
    for k in range(200):
        pick = set(rng.choice(idx, size=min(len(idx), len(sigs) and sum(e is not None for e in sigs)), replace=False))
        s2 = [allsig[i] if i in pick else None for i in range(len(df))]
        r2 = H.simulate(df, s2, risk=0.005)["trades"]
        if split == "oos" and len(r2): r2 = r2[r2.entry_time >= H.OOS_START]
        nets.append(r2.profit.sum() if len(r2) else 0)
    nets = np.array(nets)
    print("random-subset BOS longs (no filters), same #signals: mean net", round(nets.mean(), 0), "p50", round(np.median(nets), 0), "p90", round(np.percentile(nets, 90), 0), "share >= strat", round((nets >= t.profit.sum()).mean(), 3))
