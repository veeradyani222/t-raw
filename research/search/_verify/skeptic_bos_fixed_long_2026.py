import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.gold_fix.strategies import build_bos, bos_features
from research.search.gold_fix import lib as L
df = H.load("XAUUSD", "M30", split="oos")
t = pd.DatetimeIndex(df.time); m = t >= "2026-04-01"
f = bos_features(df)
hc = L.htf_close_aligned(df, "1D", lambda g: g["close"].to_numpy(float))
he = L.htf_close_aligned(df, "1D", lambda g: L.ema(g["close"].to_numpy(float), 100))
print("2026-04+: bars", m.sum(), "frac daily>EMA100", np.nanmean((hc > he)[m]).round(2), "frac atr_pct>=0.6", np.nanmean((f["atr_pct"] >= 0.6)[m]).round(2), "frac c>ma200", np.nanmean((f["c"] > f["ma"])[m]).round(2))
for kw in [dict(), dict(atrp_min=0.6), dict(tp_min_r=2.0, atrp_min=0.6), dict(tp_min_r=2.0, atrp_min=0.6, htf=("1D",100))]:
    s = build_bos(df, sides=("long",), _f=f, **kw)
    print(kw, "long signals 2026-04+:", sum(1 for i, e in enumerate(s) if e is not None and m[i]))
print(df.groupby(t.to_period("M")).close.last().loc["2025-09":].round(0).to_dict())
