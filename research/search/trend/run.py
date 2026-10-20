"""Batch scorer used by the grid scripts.
Appends one JSON line per scored run to research/search/trend/results.jsonl
and skips configs already scored (resume after a crash)."""
from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

from research.prop import harness as H
from research.search.trend import strategies as S

OUT = Path(__file__).with_name("results.jsonl")
PROCS = int(os.environ.get("TREND_PROCS", "3"))   # box has 7.5GB shared with other jobs


@lru_cache(maxsize=2)
def _load(sym, tf):
    return H.load(sym, tf, split="is")


def _key(name, sym, tf, params):
    return (name, sym, tf, json.dumps(params, sort_keys=True))


def _done():
    out = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            if "error" not in r:
                out.add(_key(r["name"], r["symbol"], r["tf"], r["params"]))
    return out


def run_one(cfg):
    try:
        return _run_one(cfg)
    except Exception as e:  # noqa: BLE001 - OOM etc. must not kill the batch
        name, fn, sym, tf, params = cfg
        return dict(name=name, symbol=sym, tf=tf, params=params, error=repr(e)[:300])


def _run_one(cfg):
    name, fn, sym, tf, params = cfg
    df = _load(sym, tf)
    t0 = time.time()
    sigs = getattr(S, fn)(df, **params)
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    r0 = s["by_risk"]["0.0025"]
    keep = ("net", "avg_month", "green_months", "max_dd", "worst_day", "trades",
            "win_rate", "challenge_pass_rate", "challenge_median_days", "worst_month")
    row = dict(name=name, fn=fn, symbol=sym, tf=tf, params=params,
               best_risk=s["best_risk"], **{k: h.get(k) for k in keep},
               # risk-normalised view at 0.25% risk: 1R = $25
               net_R=r0["net"] / 25.0, dd_R=r0["max_dd"] / 25.0,
               wd_R=r0["worst_day"] / 25.0, secs=round(time.time() - t0, 1))
    mon = h.get("monthly", {})
    yrs = {}
    for k, v in mon.items():
        yrs[k[:4]] = round(yrs.get(k[:4], 0) + v)
    row["years"] = yrs
    return row


def run(cfgs, procs=None):
    done = _done()
    cfgs = [c for c in cfgs if _key(c[0], c[2], c[3], c[4]) not in done]
    print(len(cfgs), "to run after resume-skip", flush=True)
    rows = []
    procs = procs or PROCS
    with OUT.open("a") as f:
        if procs <= 1:
            it, p = map(run_one, cfgs), None
        else:
            p = Pool(procs, maxtasksperchild=15)
            it = p.imap_unordered(run_one, cfgs)
        for row in it:
            if "error" in row:
                print("ERR", row["name"], row["symbol"], row["tf"], row["error"], flush=True)
                continue
            f.write(json.dumps(row, default=str) + "\n")
            f.flush()
            rows.append(row)
            br = f"{row['best_risk']*100:.2f}%" if row["best_risk"] else "NONE"
            print(f"{row['name']:<34}{row['symbol']:<8}{row['tf']:<4}{br:<7}"
                  f"avg/mo {row['avg_month']:>7.0f} dd {row['max_dd']:>6.0f} "
                  f"wd {row['worst_day']:>5.0f} tr {row['trades']:>5} | "
                  f"netR {row['net_R']:>6.1f} ddR {row['dd_R']:>5.1f}", flush=True)
    if p is not None:
        p.close()
    return rows
