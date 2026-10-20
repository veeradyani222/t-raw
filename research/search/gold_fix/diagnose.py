"""Where does gold BOS+CMF fail in-sample? Groups trade R by entry features."""
import sys
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.gold_fix import strategies as S

tf = sys.argv[1] if len(sys.argv) > 1 else "M30"
df = H.load("XAUUSD", tf, split="is")
sig = S.build_bos(df)
s = H.score(df, sig, name=f"bos_baseline_{tf}")
print(H.summary_line(s))
t = H.simulate(df, sig, risk=0.005)["trades"]
t["year"] = t.entry_time.dt.year
def g(col, bins=None):
    x = t[col] if bins is None else pd.cut(t[col], bins)
    r = t.groupby(x, observed=True)["r"].agg(["count", "mean", "sum"])
    r["win"] = t.groupby(x, observed=True)["r"].apply(lambda v: (v > 0).mean())
    print(f"\n== {col}\n", r.round(3).to_string())
print("\nall trades", len(t), "meanR", round(t.r.mean(), 3), "sumR", round(t.r.sum(), 1))
for col in ["year", "side", "reason", "hour", "wd", "nfp"]:
    g(col)
g("atr_pct", [0, .2, .4, .6, .8, 1.01])
g("adx", [0, 15, 20, 25, 30, 40, 100])
g("slope", [-99, -1.5, -0.5, 0, 0.5, 1.5, 99])
g("stop_atr", [0, .5, 1, 1.5, 2, 3, 5, 99])
g("tgt_r", [0, 1.2, 1.5, 2, 3, 5, 99])
g("dom", [0, 3, 7, 14, 21, 25, 31])
g("cmf", [-1, -.2, -.1, -.05, 0, .05, .1, .2, 1])
# slope aligned with trade side
t["sl_al"] = np.where(t.side == "long", t.slope, -t.slope)
g("sl_al", [-99, -1, 0, 0.5, 1, 2, 99])
t["bars_c"] = t.bars.clip(upper=100)
g("bars_c", [-1, 1, 3, 6, 12, 24, 48, 101])
