import os, sys, math
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.trend.strategies import build_gold_boll50
P = {"n": 50, "k": 2, "sl_mult": 2}
df = H.load("XAUUSD", "H4", split="oos")
sigs = build_gold_boll50(df, **P)
print(H._spec().get("XAUUSD"))
tm = pd.DatetimeIndex(df.time)
print("bars per month 2025-06..", pd.Series(1, index=tm)["2025-06":].resample("ME").sum().to_dict())
idx = [i for i, s in enumerate(sigs) if s is not None and tm[i] >= pd.Timestamp("2025-09-01")]
print("signals after 2025-09:", len(idx))
for i in idx[:12]:
    s = sigs[i]; d = abs(df.close.iloc[i] - s.sl)
    print(tm[i], s.side, "close", round(df.close.iloc[i],1), "stopdist", round(d,1), "lots@$50", round(50/(d*100+14),4), "lots@$200", round(200/(d*100+14),4))
# risk scaling: what risk is needed for min lot
for split in ("is","oos"):
    d2 = H.load("XAUUSD","H4",split=split); s2 = build_gold_boll50(d2, **P)
    for r in (0.005, 0.01, 0.02):
        res = H.simulate(d2, s2, risk=r)
        t = res["trades"]; f = d2.attrs.get("score_from")
        if f is not None: t = t[t.entry_time >= f]
        nsig = sum(1 for i,x in enumerate(s2) if x is not None and (f is None or d2.time.iloc[i] >= f))
        print(split, r, "signals", nsig, "trades", len(t), "net", round(t.profit.sum(),1), "R-sum", round(t.r.sum(),1))
# rollover cost: trades entered on bar labelled 20 fill at ~00:00 server time
for split in ("is","oos"):
    d2 = H.load("XAUUSD","H4",split=split).copy(); a=d2.attrs
    for extra in (0, 100, 200):
        d3 = d2.copy(); d3.attrs = dict(a)
        hr = pd.DatetimeIndex(d3.time).hour
        d3.loc[hr == 20, "spread"] = np.maximum(d3.loc[hr == 20, "spread"], extra)
        s3 = build_gold_boll50(d3, **P)
        sc = H.score(d3, s3, risks=(0.005,), name=f"{split}_roll{extra}")
        print(H.summary_line(sc))
    # drop hour-20 entries entirely
    s4 = build_gold_boll50(d2, **P); hr = pd.DatetimeIndex(d2.time).hour
    s4 = [None if (x is not None and hr[i] == 20) else x for i, x in enumerate(s4)]
    print(H.summary_line(H.score(d2, s4, risks=(0.005,), name=f"{split}_no20")))
