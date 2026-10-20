"""Score helper: run(name, symbol, builder, **params) -> scores with the
harness and appends one row to results.jsonl in this folder."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from research.prop import harness as H
from research.search.jpy_session import data as D
from research.search.jpy_session import strategies as S

OUT = Path(__file__).with_name("results.jsonl")
_CACHE = {}


def get(sym, tf="H1"):
    k = (sym, tf)
    if k not in _CACHE:
        _CACHE[k] = D.load(sym, tf)
    return _CACHE[k]


def run(name, sym, fn="build_session", tf="H1", quiet=False, **params):
    df = get(sym, tf)
    t0 = time.time()
    sigs = getattr(S, fn)(df, **params)
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    row = dict(name=name, symbol=sym, tf=tf, fn=fn, params=params,
               best_risk=s["best_risk"], net=h.get("net"), avg_month=h.get("avg_month"),
               green=h.get("green_months"), max_dd=h.get("max_dd"),
               worst_day=h.get("worst_day"), trades=h.get("trades"),
               win=h.get("win_rate"), worst_month=h.get("worst_month"),
               chal=h.get("challenge_pass_rate"), chal_days=h.get("challenge_median_days"),
               r025=s["by_risk"]["0.0025"]["net"], monthly=h.get("monthly"),
               source=df.attrs.get("source"))
    with OUT.open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")
    if not quiet:
        print(H.summary_line(s), f"[{time.time()-t0:.1f}s]", flush=True)
    return s, row
