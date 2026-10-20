"""Broad pre-screen sweep with screen.py (fast, R units). Writes screen.csv.
python -m research.search.mean_reversion.sweep [workers]
Skips (symbol, tf) pairs already in screen.csv, so it can be re-run as more
data files arrive."""
from __future__ import annotations

import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "screen.csv"

SPECIFIC = {
    "rsi2": [dict(n=n, lo=lo, hi=100 - lo, exit_ma=em) for n in (2, 3) for lo in (5, 15) for em in (0, 5)],
    "crsi": [dict(lo=lo, hi=100 - lo) for lo in (5, 10, 20)],
    "bb_fade": [dict(n=n, k=k) for n in (20, 50) for k in (2.0, 2.5)],
    "zscore": [dict(n=n, z_in=z) for n in (20, 100) for z in (1.5, 2.5)],
    "ibs": [dict(lo=lo, hi=1 - lo) for lo in (0.1, 0.2)],
    "nlow": [dict(n=n) for n in (5, 10, 20)],
    "wpr": [dict(n=n, lo=-100 + t, hi=-t) for n in (10, 30) for t in (5, 15)],
    "stoch": [dict(n=n, lo=t, hi=100 - t) for n in (14, 30) for t in (10, 20)],
    "vwap": [dict(dev_atr=d) for d in (1.0, 2.0, 3.0)],
}
BASE_HOLD = {"H1": 24, "H4": 12, "D1": 8, "M30": 32}


def jobs_for(tf):
    out = []
    for b, specs in SPECIFIC.items():
        if b == "vwap" and tf not in ("H1", "M30"):
            continue
        for sp, trend, sides, stop, hm in itertools.product(
                specs, (0, 200), ("long", "short", "both"), (2.0, 3.5), (1, 2)):
            p = dict(sp, trend=trend, sides=sides, stop_atr=stop, max_hold=BASE_HOLD[tf] * hm)
            if b == "vwap":
                p.pop("trend"); p["trend"] = trend
            out.append((b, p))
    return out


def run_pair(sym, tf):
    from research.prop import harness as H
    from research.search.mean_reversion import strategies as S, screen as SC
    try:
        df = H.load(sym, tf, split="is")
    except FileNotFoundError:
        return []
    rows = []
    import time as _t
    for b, p in jobs_for(tf):
        for attempt in range(30):        # the shared box sometimes runs out of RAM
            try:
                r = SC.screen(df, getattr(S, "build_" + b)(df, _raw=True, **p))
                break
            except MemoryError:
                _t.sleep(10)
        else:
            raise MemoryError("gave up")
        rows.append(dict(name=b, symbol=sym, tf=tf, params=json.dumps(p), **r))
    return rows


if __name__ == "__main__":
    from research.search.mean_reversion.grids import ALL, have
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    done = set()
    if OUT.exists():
        d = pd.read_csv(OUT)
        done = set(zip(d.symbol, d.tf))
    pairs = [(s, tf) for s in ALL for tf in ("H1", "H4", "D1") if have(s, tf) and (s, tf) not in done]
    print("pairs:", pairs, flush=True)
    if workers <= 1:
        for s_, tf in pairs:
            rows = run_pair(s_, tf)
            if rows:
                pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
            print("done", (s_, tf), len(rows), flush=True)
        sys.exit(0)
    with ProcessPoolExecutor(workers) as ex:
        futs = {ex.submit(run_pair, s, tf): (s, tf) for s, tf in pairs}
        for fu in as_completed(futs):
            rows = fu.result()
            if rows:
                pd.DataFrame(rows).to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
            print("done", futs[fu], len(rows), flush=True)
