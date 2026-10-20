"""Generic failure diagnosis: python -m research.search.gold_fix.diag_any SYMBOL TF fn 'json-params'
Groups trade R (at 0.5% risk) by features measured at the entry bar."""
import json
import sys

import numpy as np
import pandas as pd

from research.prop import harness as H
from research.search.gold_fix import lib as L
from research.search.gold_fix import strategies as S

sym, tf, fn = sys.argv[1:4]
params = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
for k, v in list(params.items()):
    if isinstance(v, list) and k in ("sides",):
        params[k] = tuple(v)
df = H.load(sym, tf, split="is")
sig = getattr(S, fn)(df, **params)
t = H.simulate(df, sig, risk=0.005)["trades"]
idx = np.searchsorted(df.time.values, t.entry_time.values)
a = L.atr(df, 14)
feat = pd.DataFrame({
    "year": df.time.dt.year.values[idx],
    "hour": df.time.dt.hour.values[idx],
    "wd": df.time.dt.weekday.values[idx],
    "atrp": L.rolling_pct_rank(a, 2000 if tf in ("M30", "H1", "M15") else 500)[idx],
    "adx": L.adx(df, 14)[0][idx],
})
t = pd.concat([t.reset_index(drop=True), feat], axis=1)
print(f"trades {len(t)} meanR {t.r.mean():.3f} sumR {t.r.sum():.1f}")


def g(col, bins=None):
    x = t[col] if bins is None else pd.cut(t[col], bins)
    r = t.groupby(x, observed=True)["r"].agg(["count", "mean", "sum"])
    print(f"\n== {col}\n", r.round(3).to_string())


for col in ["year", "side", "reason", "wd"]:
    g(col)
if tf not in ("D1", "H4"):
    g("hour")
g("atrp", [0, .2, .4, .6, .8, 1.01])
g("adx", [0, 15, 20, 25, 30, 40, 100])
t["bars_c"] = t.bars.clip(upper=200)
g("bars_c", [-1, 2, 5, 10, 20, 50, 201])
