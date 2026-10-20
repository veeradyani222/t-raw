"""Parallel scorer for breakout configs. In-sample only.

usage: python -m research.search.breakout.run <batch_name>
Batches are defined in research/search/breakout/batches.py as
BATCHES[name] = list of (name, symbol, tf, build_fn_name, params).
Results append to research/search/breakout/results.jsonl.
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results.jsonl"
_CACHE = {}


def _one(cfg):
    try:
        return _one_inner(cfg)
    except Exception as e:  # keep the batch going (e.g. memory pressure)
        _CACHE.clear()
        return dict(name=cfg[0], symbol=cfg[1], tf=cfg[2], error=f"{type(e).__name__}: {e}")


def _one_inner(cfg):
    from research.prop import harness as H
    from research.search.breakout import strategies as S
    name, sym, tf, fn, params = cfg
    assert os.environ.get("PROP_OOS") != "1"
    key = (sym, tf)
    try:
        if key not in _CACHE:
            _CACHE[key] = H.load(sym, tf, split="is")
        df = _CACHE[key]
    except FileNotFoundError as e:
        return dict(name=name, symbol=sym, tf=tf, fn=fn, params=params, error=f"missing: {e}")
    t0 = time.time()
    sigs = getattr(S, fn)(df, **params)
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    br = s["best_risk"]
    row = dict(name=name, symbol=sym, tf=tf, fn=fn, params=params, best_risk=br,
               net=round(h.get("net", 0), 1), avg_month=round(h.get("avg_month", 0), 1),
               green=round(h.get("green_months", 0), 3), max_dd=round(h.get("max_dd", 0), 1),
               worst_day=round(h.get("worst_day", 0), 1), trades=h.get("trades", 0),
               win=round(h.get("win_rate", 0), 3),
               chal=round(h.get("challenge_pass_rate", 0), 3),
               chal_days=h.get("challenge_median_days"),
               # per-trade expectancy at the lowest risk, in R-ish units
               net_025=round(s["by_risk"]["0.0025"]["net"], 1),
               months=h.get("months"), secs=round(time.time() - t0, 1))
    if br is not None:
        tr = s["trades_at_best"]
        if tr is not None and len(tr):
            yr = tr.groupby(tr.entry_time.dt.year)["profit"].sum().round(0)
            row["by_year"] = {int(k): float(v) for k, v in yr.items()}
            row["avg_r"] = round(float(tr.r.mean()), 3)
    return row


def _key(name, sym, tf, fn, params):
    return json.dumps([name, sym, tf, fn, params], sort_keys=True, default=str)


def run(cfgs, procs=6):
    done = set()
    if OUT.exists():
        for l in OUT.open():
            r = json.loads(l)
            if "error" not in r or r["error"].startswith("missing"):
                done.add(_key(r["name"], r["symbol"], r["tf"], r.get("fn"), r.get("params")))
    cfgs = [c for c in cfgs if _key(*c) not in done]
    print("to run:", len(cfgs), flush=True)
    import contextlib
    pool = Pool(procs) if procs > 1 else contextlib.nullcontext()
    with pool as p, OUT.open("a") as f:
        it = p.imap_unordered(_one, cfgs) if procs > 1 else map(_one, cfgs)
        for row in it:
            f.write(json.dumps(row, default=str) + "\n")
            f.flush()
            if "error" in row:
                print("SKIP", row["name"], row["symbol"], row["tf"], row["error"][:120], flush=True)
                continue
            br = f"{row['best_risk']*100:.2f}%" if row["best_risk"] else "NONE"
            print(f"{row['name']:<34}{row['symbol']:<7}{row['tf']:<4}{br:<7}"
                  f"avg/mo {row['avg_month']:>7.0f} dd {row['max_dd']:>6.0f} "
                  f"wd {row['worst_day']:>6.0f} n {row['trades']:>5} "
                  f"win {row['win']:.2f} chal {row['chal']:.2f} net025 {row['net_025']:>7.0f}",
                  flush=True)


if __name__ == "__main__":
    from research.search.breakout.batches import BATCHES
    run(BATCHES[sys.argv[1]], procs=int(sys.argv[2]) if len(sys.argv) > 2 else 6)
