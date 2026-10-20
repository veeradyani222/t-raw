import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, "C:/Users/veera/Desktop/mt5-trader")
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.public_eas import strategies as S
P = {"base": "bb_breakout", "dev": 2.25, "trend_n": 1000}
R = 0.005
for split in ("is", "oos"):
    df = H.load("XAUUSD", "H1", split=split)
    sigs = S.build_filtered(df, **P)
    res = H.simulate(df, sigs, risk=R)
    t = pd.DataFrame(res["trades"])
    sf = df.attrs.get("score_from")
    if sf is not None: t = t[t.entry_time >= sf]
    print("====", split, "cols", list(t.columns)[:12], "n", len(t))
    pc = "profit"
    tot = t[pc].sum(); srt = t[pc].sort_values(ascending=False)
    print("net", round(tot,1), "top1", round(srt.iloc[0],1), "top5", round(srt.iloc[:5].sum(),1), "top10", round(srt.iloc[:10].sum(),1))
    print("by side", t.groupby("side")[pc].agg(["count","sum","mean"]).round(1).to_dict())
    if "reason" in t: print(t.groupby("reason")[pc].agg(["count","sum"]).round(1).to_dict())
    t["yr"] = pd.DatetimeIndex(t.entry_time).year
    print(t.groupby("yr")[pc].agg(["count","sum"]).round(0).T.to_dict())
    # hour of entry costs
    t["hr"] = pd.DatetimeIndex(t.entry_time).hour
    print("entries at hr 0/1/23:", int(t.hr.isin([0,1,23]).sum()))
    # random baseline: same SL/TP, trend side, random bars, matched density
    c = df.close.to_numpy(float); a = S.atr(df, 14); tr = S.sma(c, 1000)
    n = len(df); real = sum(e is not None for e in sigs)
    rng = np.random.default_rng(1); nets = []
    for k in range(30):
        pick = rng.random(n) < real / n
        out = []
        for i in range(n):
            if pick[i] and np.isfinite(tr[i]) and np.isfinite(a[i]) and i > 1000:
                if c[i] > tr[i]: out.append(H.Entry("long", c[i]-1.5*a[i], c[i]+3.75*a[i]))
                else: out.append(H.Entry("short", c[i]+1.5*a[i], c[i]-3.75*a[i]))
            else: out.append(None)
        rr = H.simulate(df, out, risk=R); tt = pd.DataFrame(rr["trades"])
        if sf is not None: tt = tt[tt.entry_time >= sf]
        nets.append(tt[pc].sum())
    nets = np.array(nets)
    print("random trend-side baseline net: mean", round(nets.mean()), "p50", round(np.median(nets)), "p90", round(np.percentile(nets,90)), "max", round(nets.max()), "frac >= real", (nets >= tot).mean())
