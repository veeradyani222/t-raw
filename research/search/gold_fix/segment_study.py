"""Descriptive: do intraday session returns predict the next session? (H1, in-sample)
Segments in server hours: ASIA 1-8, LDN 9-15, NY 16-23. Returns in units of daily ATR."""
import numpy as np
import pandas as pd

from research.prop import harness as H

for sym in ["XAUUSD", "XAGUSD"]:
    df = H.load(sym, "H1", split="is")
    df["day"] = df.time.dt.normalize()
    df["hr"] = df.time.dt.hour
    seg = pd.cut(df.hr, [0, 8, 15, 23], labels=["ASIA", "LDN", "NY"], include_lowest=True)
    df["seg"] = seg
    r = df.assign(ret=df.close - df.open).groupby(["day", "seg"], observed=True).ret.sum().unstack()
    rng = df.groupby("day").apply(lambda g: g.high.max() - g.low.min(), include_groups=False)
    atr = rng.rolling(20).mean().shift(1)
    z = r.div(atr, axis=0).dropna()
    z["prevNY"] = z.NY.shift(1)
    z["prevDAY"] = (z.ASIA + z.LDN + z.NY).shift(1)
    z["half"] = np.where(z.index.year < 2020, "A", "B")
    print(sym, len(z))
    for a, b in [("ASIA", "LDN"), ("LDN", "NY"), ("ASIA", "NY"), ("prevNY", "ASIA"), ("prevDAY", "ASIA"),
                 ("prevDAY", "LDN"), ("prevDAY", "NY")]:
        out = []
        for hlf, g in z.groupby("half"):
            g = g.dropna()
            c = g[a].corr(g[b])
            # sign strategy: trade b in direction of a when |a| > 0.3
            m = g[a].abs() > 0.3
            pnl = (np.sign(g[a]) * g[b])[m]
            out.append(f"{hlf}: corr {c:+.3f}  follow|a|>.3 mean {pnl.mean():+.3f} n={m.sum()}")
        print(f"  {a:>7} -> {b:<5}", " | ".join(out))
