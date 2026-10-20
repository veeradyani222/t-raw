"""Fine pre-screen of long-only dip-buying on indices (and any pairs passed).
python -m research.search.mean_reversion.sweep_fine OUTNAME SYM:TF [SYM:TF ...]
Writes <OUTNAME>.csv (screen.py metrics, R units)."""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
HOLD = {"M30": (16, 48), "H1": (12, 24, 48), "H4": (6, 12, 24), "D1": (4, 8, 16)}


def grid(tf):
    common = list(itertools.product((0, 50, 200), (2.0, 3.0, 4.5, 6.0), HOLD[tf]))
    spec = {
        "wpr": [dict(n=n, lo=lo, hi=-100 - lo, exit_lvl=ex) for n in (5, 7, 10, 14, 20)
                for lo in (-95, -90, -85, -80, -75) for ex in (-50, -30)],
        "nlow": [dict(n=n) for n in (3, 5, 7, 10, 15, 20)],
        "ibs": [dict(lo=lo, hi=1 - lo) for lo in (0.1, 0.15, 0.2, 0.25, 0.3)],
        "rsi2": [dict(n=n, lo=lo, hi=100 - lo, exit_ma=em) for n in (2, 3, 4)
                 for lo in (5, 10, 15, 20, 25, 30) for em in (0, 3, 5, 10)],
        "bb_fade": [dict(n=n, k=k) for n in (10, 20, 30, 50) for k in (1.5, 2.0, 2.5)],
        "zscore": [dict(n=n, z_in=z, z_out=zo) for n in (10, 20, 50, 100)
                   for z in (1.0, 1.5, 2.0, 2.5) for zo in (0.0, 0.5)],
        "stoch": [dict(n=n, lo=lo, hi=100 - lo) for n in (5, 9, 14, 30) for lo in (5, 10, 20, 30)],
    }
    for b, specs in spec.items():
        for sp, (trend, stop, hold) in itertools.product(specs, common):
            yield b, dict(sp, sides="long", trend=trend, stop_atr=stop, max_hold=hold)


def main(out, pairs):
    from research.prop import harness as H
    from research.search.mean_reversion import strategies as S, screen as SC
    path = HERE / f"{out}.csv"
    for pt in pairs:
        sym, tf = pt.split(":")
        try:
            df = H.load(sym, tf, split="is")
        except FileNotFoundError:
            print("missing", pt, flush=True); continue
        rows = []
        for b, p in grid(tf):
            for _ in range(30):
                try:
                    r = SC.screen(df, getattr(S, "build_" + b)(df, _raw=True, **p)); break
                except MemoryError:
                    time.sleep(10)
            rows.append(dict(name=b, symbol=sym, tf=tf, params=json.dumps(p), **r))
        pd.DataFrame(rows).to_csv(path, mode="a", header=not path.exists(), index=False)
        print("done", pt, len(rows), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
