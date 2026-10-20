"""Grid runner: python -m research.search.mean_reversion.run <grid_name>
Appends one row per scored run to results.csv in this folder."""
from __future__ import annotations

import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results.csv"
FIELDS = ["grid", "name", "symbol", "tf", "params", "best_risk", "net", "avg_month",
          "green_months", "max_dd", "worst_day", "trades", "win_rate",
          "challenge_pass_rate", "challenge_median_days", "r_at_025"]

_cache = {}


def _load(sym, tf):
    from research.prop import harness as H
    k = (sym, tf)
    if k not in _cache:
        _cache[k] = H.load(sym, tf, split="is")
    return _cache[k]


def run_one(job):
    from research.prop import harness as H
    from research.search.mean_reversion import strategies as S
    name, sym, tf, params = job
    try:
        df = _load(sym, tf)
    except FileNotFoundError:
        return dict(name=name, symbol=sym, tf=tf, params=json.dumps(params), best_risk="MISSING")
    sigs = getattr(S, "build_" + name)(df, **params)
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    tb = s["trades_at_best"]
    if tb is None:  # none safe: express the 2% run in R (1R = $200)
        rtot = s["by_risk"]["0.02"].get("net", 0) / 200.0
    else:
        rtot = float(tb["r"].sum()) if len(tb) else 0.0
    return dict(name=name, symbol=sym, tf=tf, params=json.dumps(params),
                best_risk=s["best_risk"], net=round(h.get("net", 0), 0),
                avg_month=round(h.get("avg_month", 0), 1),
                green_months=round(h.get("green_months", 0), 2),
                max_dd=round(h.get("max_dd", 0), 0), worst_day=round(h.get("worst_day", 0), 0),
                trades=h.get("trades", 0), win_rate=round(h.get("win_rate", 0), 3),
                challenge_pass_rate=round(h.get("challenge_pass_rate", 0), 3),
                challenge_median_days=h.get("challenge_median_days"),
                r_at_025=round(rtot, 1))   # total R (edge independent of sizing)


def run_grid(grid, jobs, workers=10):
    new = not OUT.exists()
    t0 = time.time()
    rows = []
    with open(OUT, "a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        for j in jobs:              # sequential: the shared box is short on RAM
            for _ in range(30):
                try:
                    r = run_one(j); break
                except MemoryError:
                    time.sleep(10)
            r["grid"] = grid
            w.writerow(r)
            f.flush()
            rows.append(r)
    rows.sort(key=lambda r: (r.get("best_risk") not in (None, "MISSING"), r.get("avg_month", -1e9)),
              reverse=True)
    for r in rows:
        print(f"{r['name']:<10}{r['symbol']:<8}{r['tf']:<4} risk={r['best_risk']!s:<7} "
              f"avg/mo={r.get('avg_month')!s:>7} dd={r.get('max_dd')!s:>6} wd={r.get('worst_day')!s:>6} "
              f"n={r.get('trades')!s:>5} R={r.get('r_at_025')!s:>6} wr={r.get('win_rate')} "
              f"chal={r.get('challenge_pass_rate')} {r['params']}")
    print(f"{len(jobs)} runs in {time.time()-t0:.0f}s")
    return rows


if __name__ == "__main__":
    # python -m ...run GRIDNAME            (function in grids.py)
    # python -m ...run GRIDNAME jobs.json  ([[builder, sym, tf, params], ...])
    g = sys.argv[1]
    if len(sys.argv) > 2:
        jobs = [tuple(j) for j in json.loads(Path(sys.argv[2]).read_text())]
    else:
        from research.search.mean_reversion import grids
        jobs = getattr(grids, g)()
    run_grid(g, jobs)
