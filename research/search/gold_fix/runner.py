"""Sequential, in-process scorer with resume (machine is memory-starved; no pools).
job = (name, symbol, tf, build_fn_name, params, score_kw). Appends every scored
run to results.jsonl in this folder; names already there are skipped."""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import gc, json, sys, time
from pathlib import Path
OUT = Path(__file__).with_name("results.jsonl")
_cache = {}

def _load(sym, tf):
    from research.prop import harness as H
    key = (sym, tf)
    if key not in _cache:
        _cache.clear(); gc.collect()
        _cache[key] = H.load(sym, tf, split="is")
    return _cache[key]

def score_one(job):
    name, sym, tf, fn, params, kw = job
    from research.prop import harness as H
    from research.search.gold_fix import strategies as S
    df = _load(sym, tf)
    sig = getattr(S, fn)(df, **params)
    s = H.score(df, sig, name=name, **(kw or {}))
    h = s["headline"]
    return dict(name=name, symbol=sym, tf=tf, fn=fn, params=params, score_kw=kw or {},
                best_risk=s["best_risk"], net=h.get("net"), avg_month=h.get("avg_month"),
                green=h.get("green_months"), max_dd=h.get("max_dd"), worst_day=h.get("worst_day"),
                trades=h.get("trades"), win=h.get("win_rate"), chal=h.get("challenge_pass_rate"),
                chal_days=h.get("challenge_median_days"), worst_month=h.get("worst_month"),
                r025=s["by_risk"]["0.0025"].get("net"), monthly=h.get("monthly"),
                by_risk={k: (round(v.get("net", 0)), round(v.get("max_dd", 0)), round(v.get("worst_day", 0))) for k, v in s["by_risk"].items()},
                line=H.summary_line(s))

def done_names():
    if not OUT.exists():
        return set()
    return {json.loads(l)["name"] for l in OUT.read_text().splitlines() if l.strip()}

def run(jobs, retries=4):
    for attempt in range(retries):
        todo = [j for j in jobs if j[0] not in done_names()]
        if not todo:
            return
        for j in todo:
            try:
                rec = score_one(j)
            except Exception as e:
                print("job failed:", j[0], type(e).__name__, str(e)[:100], flush=True)
                _cache.clear(); gc.collect(); time.sleep(3)
                continue
            print(rec["line"], "| net@0.25%", round(rec["r025"] or 0), flush=True)
            with OUT.open("a") as f:
                f.write(json.dumps(rec, default=str) + "\n")
            gc.collect()
