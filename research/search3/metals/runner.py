"""Scoring runner for search3/metals. Pool(2) max. Appends to results.jsonl.

Usage: python research/search3/metals/runner.py <batch_name> [--smoke]
Batches are defined in grids.py as functions returning a list of jobs:
    dict(name, fn, symbol, tf, params)
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from multiprocessing import Pool
from pathlib import Path

os.environ["PROP_OOS"] = "1"
import numpy as np
import pandas as pd

from research.prop import harness as H

HERE = Path(__file__).resolve().parent
OUT = HERE / "results.jsonl"

# ---------------------------------------------------------------- costs --
# XPTUSD / XPDUSD: symbol_specs contract = 1 oz, vol_step 0.1. Spread column
# (point 0.001) medians over the window: XPT 2220 pts = $2.22, XPD 3011 pts =
# $3.01 (wider 00:00-02:00). Floors below; harness takes max(floor, bar spread).
# $14/lot commission is per 100-oz metal lot; with contract=1 it would be
# $14/oz (absurd) and the true $0.14/oz (~0.01%) is negligible next to the
# 0.14-0.25% spread, so both are treated like indices (no commission).
H.SPREAD_FLOOR.update({"XPTUSD": 2.0, "XPDUSD": 3.0})
H.INDICES = set(H.INDICES) | {"XPTUSD", "XPDUSD"}
_orig_pip = H._pip


def _pip(symbol):
    if symbol in ("XPTUSD", "XPDUSD"):
        return 0.1
    return _orig_pip(symbol)


H._pip = _pip

# ------------------------------------------------------- bad-tick cleaning --
# XPTUSD / XPDUSD 2026-10-27 19:00-21:00 server: low = 0.001/0.003 and (XPD)
# high = 48307.867. Clamp wicks to within 10% of the bar body.
_orig_load = H.load
BAD = {}


def load(symbol, tf="H1", split="is", warmup_bars=3000):
    df = _orig_load(symbol, tf, split, warmup_bars)
    body_hi = np.maximum(df["open"], df["close"])
    body_lo = np.minimum(df["open"], df["close"])
    bad_lo = df["low"] < 0.9 * body_lo
    bad_hi = df["high"] > 1.1 * body_hi
    nbad = int(bad_lo.sum() + bad_hi.sum())
    if nbad:
        df.loc[bad_lo, "low"] = body_lo[bad_lo]
        df.loc[bad_hi, "high"] = body_hi[bad_hi]
        BAD[(symbol, tf)] = nbad
    return df


H.load = load

_DF = {}


def get_df(symbol, tf):
    k = (symbol, tf)
    if k not in _DF:
        _DF[k] = H.load(symbol, tf, split="oos")
    return _DF[k]


def run_job(job):
    from research.search3.metals import strategies as S
    t0 = time.time()
    try:
        df = get_df(job["symbol"], job["tf"])
        build = getattr(S, job["fn"])
        sigs = build(df, **job["params"])
        n_sig = sum(1 for s in sigs if s is not None)
        s = H.score(df, sigs, name=job["name"])
        h = s["headline"]
        br = s["best_risk"]
        row = dict(batch=job.get("batch"), name=job["name"], fn=job["fn"], symbol=job["symbol"],
                   tf=job["tf"], params=job["params"], best_risk=br, signals=n_sig,
                   net=round(h.get("net", 0), 1), avg_month=round(h.get("avg_month", 0), 1),
                   green=round(h.get("green_months", 0), 3), max_dd=round(h.get("max_dd", 0), 1),
                   worst_day=round(h.get("worst_day", 0), 1), trades=h.get("trades", 0),
                   win=round(h.get("win_rate", 0), 3), chal=round(h.get("challenge_pass_rate", 0), 3),
                   months=h.get("months"),
                   net_025=round(s["by_risk"]["0.0025"].get("net", 0), 1),
                   monthly=h.get("monthly"), secs=round(time.time() - t0, 1))
    except Exception as e:  # noqa
        row = dict(batch=job.get("batch"), name=job["name"], fn=job["fn"], symbol=job["symbol"],
                   tf=job["tf"], params=job["params"], error=f"{type(e).__name__}: {e}",
                   tb=traceback.format_exc()[-800:])
    return row


def run_batch(jobs, procs=2, label=None):
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                r = json.loads(line)
                done.add((r.get("batch"), r["name"], r["symbol"], r["tf"]))
            except Exception:
                pass
    todo = [j for j in jobs if (j.get("batch"), j["name"], j["symbol"], j["tf"]) not in done]
    print(f"{label or ''}: {len(jobs)} jobs, {len(todo)} to run", flush=True)
    t0 = time.time()
    with OUT.open("a") as f:
        if procs <= 1:
            it = map(run_job, todo)
        else:
            pool = Pool(procs)
            it = pool.imap_unordered(run_job, todo, chunksize=2)
        for k, row in enumerate(it, 1):
            f.write(json.dumps(row, default=str) + "\n")
            f.flush()
            if "error" in row:
                print(f"[{k}/{len(todo)}] ERROR {row['name']} {row['symbol']} {row['tf']}: {row['error']}", flush=True)
            else:
                br = f"{row['best_risk']*100:.2f}%" if row["best_risk"] else "none"
                print(f"[{k}/{len(todo)}] {row['name']:<34} {row['symbol']:<7}{row['tf']:<4} risk {br:<6} "
                      f"avg/mo {row['avg_month']:>7.1f} net {row['net']:>8.0f} dd {row['max_dd']:>7.0f} "
                      f"wd {row['worst_day']:>6.0f} tr {row['trades']:>4} win {row['win']:.2f} ({row['secs']}s)", flush=True)
        if procs > 1:
            pool.close(); pool.join()
    print(f"batch done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    from research.search3.metals import grids
    name = sys.argv[1]
    jobs = getattr(grids, name)()
    for j in jobs:
        j.setdefault("batch", name)
    procs = 1 if "--serial" in sys.argv else 2
    if "--smoke" in sys.argv:
        jobs = jobs[: int(sys.argv[sys.argv.index("--smoke") + 1])]
    run_batch(jobs, procs=procs, label=name)
