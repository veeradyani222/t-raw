"""Score asia_indices configs with the prop harness on the locked window (PROP_OOS=1, Pool(2) max).
Usage: python research/search3/asia_indices/run.py <batch_name|all|b1,b2,...> [workers] [out_file]
Appends rows to results.jsonl (skips jobs already scored)."""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ["PROP_OOS"] = "1"
HERE = Path(__file__).resolve().parent
OUT = HERE / "results.jsonl"   # overridden by argv[3]
sys.path.insert(0, str(HERE.parents[2]))

_cache = {}


def _load(sym, tf):
    from research.prop import harness as H
    from research.search3.asia_indices import strategies  # noqa: F401 (patches harness)
    key = (sym, tf)
    if key not in _cache:
        _cache.clear()
        _cache[key] = H.load(sym, tf, split="oos")
    return _cache[key]


def job_key(j):
    name, fn, sym, tf, params = j
    return f"{fn}|{sym}|{tf}|{json.dumps(params, sort_keys=True)}"


def one(job):
    from research.prop import harness as H
    from research.search3.asia_indices import strategies as S
    name, fn, sym, tf, params = job
    t0 = time.time()
    try:
        df = _load(sym, tf)
        sigs = getattr(S, fn)(df, **params)
        s = H.score(df, sigs, name=name)
        h = s["headline"]
        row = dict(name=name, build_fn=fn, symbol=sym, tf=tf, params=params,
                   best_risk=s["best_risk"], n_sig=int(sum(x is not None for x in sigs)),
                   **{k: h.get(k) for k in ("net", "avg_month", "green_months", "max_dd",
                                            "worst_day", "trades", "win_rate",
                                            "challenge_pass_rate")},
                   secs=round(time.time() - t0, 1))
        print(H.summary_line(s), flush=True)
    except Exception as e:  # noqa
        row = dict(name=name, build_fn=fn, symbol=sym, tf=tf, params=params, error=repr(e))
        print("ERR", name, sym, tf, repr(e), flush=True)
    row["key"] = job_key(job)
    return row


def main():
    from research.search3.asia_indices import batches
    global OUT
    batch = sys.argv[1]
    if len(sys.argv) > 3:
        OUT = Path(sys.argv[3])
    if batch == "all":
        jobs = batches.all_jobs()
    else:
        jobs = []
        for b in batch.split(","):
            jobs += getattr(batches, b)()
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                done.add(json.loads(line)["key"])
            except Exception:
                pass
    jobs = [j for j in jobs if job_key(j) not in done]
    workers = min(int(sys.argv[2]) if len(sys.argv) > 2 else 2, 2)
    print(f"{batch}: {len(jobs)} jobs to run, {workers} workers", flush=True)
    with OUT.open("a") as f:
        if workers <= 1:
            for j in jobs:
                f.write(json.dumps(one(j)) + "\n"); f.flush()
        else:
            with Pool(workers) as p:
                for row in p.imap_unordered(one, jobs):
                    f.write(json.dumps(row) + "\n"); f.flush()
    print("done", flush=True)


if __name__ == "__main__":
    main()
