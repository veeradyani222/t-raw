"""DE40 sanity: volume/range by clock time, and cost stress on the top configs."""
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.breakout import strategies as S
df = H.load("DE40", "M30", split="is")
t = pd.DatetimeIndex(df.time)
g = pd.DataFrame({"hm": t.hour + t.minute / 60, "rng": df.high - df.low, "vol": df.tick_volume})
print(g.groupby("hm").median().round(1).T.to_string())
DEB = dict(rs=10, re=10.5, te=12.5, exit_h=18, sl="far", tp_r=None, trend="d", min_rng=0.1)
for name, p in (("base", {}), ("frac0.75", dict(sl_frac=0.75)), ("atr0.25", dict(sl="atr", sl_atr=0.25)),
                ("open9", dict(rs=9, re=9.5, te=11.5))):
    sig = S.build_session_orb(df, **{**DEB, **p})
    for sm in (1.0, 2.0, 3.0):
        s = H.score(df, sig, spread_mult=sm, risks=(0.0025, 0.005), name=f"{name} spread x{sm}")
        print(H.summary_line(s))
