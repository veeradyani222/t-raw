"""Batch runner for search3/exotics.
    python -m research.search3.exotics.run <batch> [...]   (Pool(2))
Scores on split="oos" (PROP_OOS=1, counted from 2024-10-20) and appends one
JSON line per run to results.jsonl. Also runs the look-ahead check once per
(builder, params) on the first symbol it meets (lookahead.jsonl)."""
from __future__ import annotations

import json
import os
import random
import sys
import time
import traceback
from multiprocessing import Pool
from pathlib import Path

os.environ["PROP_OOS"] = "1"

from research.prop import harness as H                      # noqa: E402
from research.search3.exotics import strategies as S        # noqa: E402
from research.search3.exotics.batches import BATCHES        # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "results.jsonl"
LA = HERE / "lookahead.jsonl"
_cache = {}
_la_done = set()


def _load(sym, tf):
    S.patch_harness()
    k = (sym, tf)
    if k not in _cache:
        if len(_cache) > 3:
            _cache.clear()
        df = H.load(sym, tf, split="oos")
        df = S.clean(df)
        _cache[k] = df
    return _cache[k]


def _sig_key(e):
    if e is None:
        return None
    return (e.side, round(e.sl, 10), None if e.tp is None else round(e.tp, 10), e.max_hold,
            e.exit_hour, getattr(e.manage, "__name__", None), tuple(sorted(e.meta.items())))


def lookahead_check(df, fn, params, seed=0):
    full = [_sig_key(e) for e in getattr(S, "build_" + fn)(df, **params)]
    rng = random.Random(seed)
    n = len(df)
    bad = 0
    for k in [rng.randint(n // 3, n - 1) for _ in range(5)]:
        sub = df.iloc[:k].reset_index(drop=True)
        sub.attrs.update(df.attrs)
        part = [_sig_key(e) for e in getattr(S, "build_" + fn)(sub, **params)]
        if part != full[:k]:
            bad += 1
    return bad == 0


def run_one(args):
    name, fn, sym, tf, params, batch = args
    try:
        df = _load(sym, tf)
        sigs = getattr(S, "build_" + fn)(df, **params)
        s = H.score(df, sigs, name=name)
        h = s["headline"]
        la_key = (fn, json.dumps(params, sort_keys=True))
        causal = None
        if la_key not in _la_done:
            causal = lookahead_check(df, fn, params)
            _la_done.add(la_key)
            with LA.open("a") as f:
                f.write(json.dumps(dict(fn=fn, params=params, symbol=sym, tf=tf, ok=causal)) + "\n")
        row = dict(batch=batch, name=name, build_fn=fn, symbol=sym, tf=tf, params=params,
                   best_risk=s["best_risk"], causal=causal,
                   **{k: h.get(k) for k in ("net", "avg_month", "green_months", "max_dd",
                                            "worst_day", "trades", "challenge_pass_rate",
                                            "win_rate", "worst_month")})
        with OUT.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print(H.summary_line(s), flush=True)
        return row
    except Exception as e:
        print("ERR", name, sym, tf, repr(e), flush=True)
        traceback.print_exc()
        return None


def main(names, procs=2):
    jobs = []
    only = set(os.environ.get("SYMS", "").split(",")) - {""}
    for b in names:
        for (name, fn, sym, tf, params) in BATCHES[b]():
            if only and sym not in only:
                continue
            jobs.append((name, fn, sym, tf, params, b))
    # group by (sym, tf) so each worker's cache is hit
    jobs.sort(key=lambda j: (j[2], j[3]))
    t0 = time.time()
    if procs == 1:
        for j in jobs:
            run_one(j)
    else:
        with Pool(procs) as p:
            for _ in p.imap(run_one, jobs, chunksize=4):
                pass
    print(f"-- {len(jobs)} jobs done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    procs = int(os.environ.get("PROCS", "2"))
    main(sys.argv[1:], procs)
