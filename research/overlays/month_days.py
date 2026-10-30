"""Day-by-day backtest P&L of the live mix for one month: 66 vs 51 (no indices).
    python -m research.overlays.month_days <cache_dir> <YYYY-MM>
"""
import os, sys
os.environ.setdefault("PROP_OOS", "1")
from pathlib import Path
import numpy as np, pandas as pd
from research.overlays import runs

IDX = {"DE40", "US30", "US500", "USTEC"}

def daily_curve(cache, window="A"):
    mix = runs.load_mix(); data = runs.load(cache, window, mix)
    curves = [d[0.0][0] for d in data]
    idx = pd.DatetimeIndex(sorted(set().union(*[set(c.time) for c in curves])))
    C = np.vstack([c.set_index("time").close.reindex(idx).ffill().fillna(0).to_numpy() for c in curves])
    keep = np.array([m["symbol"] not in IDX for m in mix])
    out = {}
    for name, mask in (("66 strategies", np.ones(len(mix), bool)), ("51 (no indices)", keep)):
        s = pd.Series(C[mask].sum(0), idx); out[name] = s.groupby(s.index.normalize()).last()
    return pd.DataFrame(out)

if __name__ == "__main__":
    cache, ym = Path(sys.argv[1]), sys.argv[2]
    d = daily_curve(cache)
    y, m = map(int, ym.split("-")); start = pd.Timestamp(y, m, 1); end = pd.Timestamp(y + (m == 12), m % 12 + 1, 1)
    chg = d[(d.index >= start - pd.Timedelta(days=4)) & (d.index < end)].diff().dropna()
    chg = chg[chg.index.month == m].round(0)
    chg.index = [f"{t:%a %d %b}" for t in chg.index]
    print(chg.to_string()); print("\nmonth total:", chg.sum().round(0).to_dict(), "| green days:", (chg > 0).sum().to_dict(), "of", len(chg))
    mon = d.groupby(d.index.to_period("M")).last().diff().dropna().round(0)
    print("\nmonthly totals:"); print(mon.tail(6).to_string())
