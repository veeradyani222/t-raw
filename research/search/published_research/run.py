"""Batch runner: python -m research.search.published_research.run <batch>
Appends one JSON line per scored run to results.jsonl (in-sample only)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from research.prop import harness as H
from research.search.published_research import strategies as S
from research.search.published_research.batches import BATCHES

OUT = Path(__file__).with_name("results.jsonl")
_cache = {}


def _load(sym, tf):
    k = (sym, tf)
    if k not in _cache:
        _cache[k] = H.load(sym, tf, split="is")
    return _cache[k]


def run_one(job):
    name, fn, sym, tf, params = job
    try:
        df = _load(sym, tf)
    except FileNotFoundError:
        return dict(name=name, symbol=sym, tf=tf, params=params, missing=True)
    t0 = time.time()
    sigs = getattr(S, fn)(df, **params)
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    rec = dict(name=name, fn=fn, symbol=sym, tf=tf, params=params, best_risk=s["best_risk"],
               line=H.summary_line(s), secs=round(time.time() - t0, 1),
               **{k: h.get(k) for k in ("net", "avg_month", "green_months", "max_dd",
                                         "worst_day", "trades", "win_rate", "worst_month",
                                         "challenge_pass_rate", "challenge_median_days")},
               r025={k: s["by_risk"]["0.0025"].get(k) for k in ("net", "max_dd", "worst_day", "trades")})
    # yearly at best risk for robustness
    if s["best_risk"] is not None:
        m = h["monthly"]
        yr = {}
        for k, v in m.items():
            yr[k[:4]] = round(yr.get(k[:4], 0) + v, 0)
        rec["yearly"] = yr
    return rec


def _done():
    seen = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            if not r.get("missing") and not r.get("error"):
                seen.add((r["name"], r["symbol"], r["tf"], json.dumps(r["params"], sort_keys=True)))
    return seen


def _safe(job):
    try:
        return run_one(job)
    except Exception as e:  # noqa: BLE001 - keep the batch going
        return dict(name=job[0], symbol=job[2], tf=job[3], params=job[4], error=repr(e)[:300])


def main(batch):
    seen = _done()
    jobs = [j for j in BATCHES[batch]() if (j[0], j[2], j[3], json.dumps(j[4], sort_keys=True)) not in seen]
    for job in jobs:          # serial: the box is memory-constrained
        rec = _safe(job)
        with OUT.open("a") as f:
            f.write(json.dumps(rec, default=str) + chr(10))
        print(rec.get("line") or f"SKIP {rec['name']} {rec['symbol']} {rec['tf']} {rec.get('error', 'missing')}",
              rec.get("yearly", ""), flush=True)
        _cache.clear() if len(_cache) > 3 else None


if __name__ == "__main__":
    main(sys.argv[1])
