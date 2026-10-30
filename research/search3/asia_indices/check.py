"""Look-ahead check: build(df) vs build(df.iloc[:k]) for 5 random k; every Entry at index < k
must be identical. Usage: python check.py  (checks the candidate list in CANDS, or pass a
results.jsonl row count N to check the top-N rows by avg_month)."""
from __future__ import annotations
import json, os, random, sys
os.environ["PROP_OOS"] = "1"
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from research.search3.asia_indices import strategies as S
from research.prop import harness as H


def ent_sig(e):
    if e is None:
        return None
    return (e.side, round(float(e.sl), 6), None if e.tp is None else round(float(e.tp), 6),
            e.max_hold, e.exit_hour, e.manage is not None, json.dumps(e.meta, sort_keys=True))


def check(fn, sym, tf, params, seed=0, ks=5):
    df = H.load(sym, tf, split="oos")
    full = [ent_sig(e) for e in getattr(S, fn)(df, **params)]
    rng = random.Random(seed)
    n = len(df)
    bad = []
    for k in [rng.randint(n // 2, n - 10) for _ in range(ks)]:
        sub = df.iloc[:k].reset_index(drop=True)
        sub.attrs.update(df.attrs)
        part = [ent_sig(e) for e in getattr(S, fn)(sub, **params)]
        diff = [i for i in range(k) if full[i] != part[i]]
        if diff:
            bad.append((k, len(diff), diff[:5]))
    return bad


def main():
    rows = [json.loads(l) for l in (HERE / "results.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r.get("best_risk") and (r.get("avg_month") or 0) > 0]
    rows.sort(key=lambda r: -r["avg_month"])
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    for r in rows[:n]:
        bad = check(r["build_fn"], r["symbol"], r["tf"], r["params"])
        print("OK " if not bad else "BUG", r["build_fn"], r["symbol"], r["tf"], r["params"], bad, flush=True)


if __name__ == "__main__":
    main()
