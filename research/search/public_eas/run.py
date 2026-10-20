"""Batch runner: python -m research.search.public_eas.run <jobfile.py-name>

Each job = (label, builder_name, symbol, tf, params). Results append to
research/search/public_eas/results.jsonl (one line per scored run).
In-sample only (split='is')."""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json
import sys
import time
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from research.prop import harness as H
from research.search.public_eas import strategies as S

OUT = Path(__file__).with_name("results.jsonl")


def weekly_from_daily(df):
    """Causal W1 bars from D1 (each weekly bar is only used after it closed,
    because signals are taken on the bar's own close)."""
    t = pd.DatetimeIndex(df["time"])
    key = t.normalize() - pd.to_timedelta(t.weekday, unit="D")
    g = df.groupby(key)
    w = pd.DataFrame({"time": g["time"].first(), "open": g["open"].first(),
                      "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "tick_volume": g["tick_volume"].sum(),
                      "spread": g["spread"].max(), "conv": g["conv"].last()})
    w = w.reset_index(drop=True)
    w.attrs.update(df.attrs)
    w.attrs["tf"] = "W1"
    return w


@lru_cache(maxsize=8)
def get_df(sym, tf):
    if tf == "W1":
        return weekly_from_daily(H.load(sym, "D1", split="is"))
    return H.load(sym, tf, split="is")


def run_job(job):
    label, bname, sym, tf, params = job
    try:
        df = get_df(sym, tf)
    except FileNotFoundError:
        return dict(label=label, ea=bname, symbol=sym, tf=tf, params=params, missing=True)
    t0 = time.time()
    params = dict(params)
    sm = params.pop("_spread", 1.0)
    sigs = S.BUILDERS[bname](df, **params)
    s = H.score(df, sigs, name=label, spread_mult=sm)
    h = s["headline"]
    return dict(label=label, ea=bname, symbol=sym, tf=tf, params=params,
                best_risk=s["best_risk"], net=round(h.get("net", 0), 1),
                avg_month=round(h.get("avg_month", 0), 1),
                green=round(h.get("green_months", 0), 3),
                max_dd=round(h.get("max_dd", 0), 1),
                worst_day=round(h.get("worst_day", 0), 1),
                trades=h.get("trades", 0), win=round(h.get("win_rate", 0), 3),
                chal=round(h.get("challenge_pass_rate", 0), 3),
                chal_days=h.get("challenge_median_days"),
                worst_month=round(h.get("worst_month", 0), 1),
                r025=s["by_risk"]["0.0025"]["net"],
                secs=round(time.time() - t0, 1), line=H.summary_line(s))


def run(jobs, procs=3, tag=""):
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            done.add((r["label"], r["symbol"], r["tf"]))
    todo = [j for j in jobs if (j[0], j[2], j[3]) not in done]
    print(f"{len(jobs)} jobs, {len(todo)} to run", flush=True)
    res = []
    with Pool(procs, maxtasksperchild=20) as p, OUT.open("a") as f:
        for r in p.imap_unordered(run_job, todo, chunksize=1):
            r["tag"] = tag
            f.write(json.dumps(r, default=str) + "\n")
            f.flush()
            print("MISSING " + r["symbol"] + " " + r["tf"] if r.get("missing") else r["line"], flush=True)
            res.append(r)
    return res
