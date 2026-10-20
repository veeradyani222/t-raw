import sys
import numpy as np, pandas as pd
from research.prop import harness as H
for sym in sys.argv[1:]:
    df = H.load(sym, "H1", split="is")
    r = np.log(df.close).diff()
    hr = df.time.dt.hour
    yr = df.time.dt.year
    g = pd.DataFrame({"r": r, "hr": hr, "yr": yr}).dropna()
    t = g.groupby("hr").r.agg(["mean", "std", "count"])
    t["t"] = t["mean"] / t["std"] * np.sqrt(t["count"])
    # fraction of years with same sign
    py = g.groupby(["yr", "hr"]).r.mean().unstack()
    t["yrs_pos"] = (py > 0).sum()
    t["mean_bp"] = t["mean"] * 1e4
    print(sym); print(t[["mean_bp", "t", "yrs_pos"]].round(2).T.to_string())
