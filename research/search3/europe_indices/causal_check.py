"""Look-ahead check: build(df) vs build(df.iloc[:k]) for 5 random k per
candidate; every Entry at index < k must be identical (side, sl, tp,
max_hold, exit_hour). Usage: python causal_check.py [results.jsonl top-N | all builders]"""
import sys, json, random
sys.path.insert(0, ".")
from pathlib import Path
from research.search3.europe_indices.common import *
from research.search3.europe_indices import strategies as S

HERE = Path(__file__).resolve().parent


def same(a, b):
    if a is None or b is None:
        return a is b
    return (a.side == b.side and abs(a.sl - b.sl) < 1e-9 and
            ((a.tp is None and b.tp is None) or (a.tp is not None and b.tp is not None and abs(a.tp - b.tp) < 1e-9))
            and a.max_hold == b.max_hold and a.exit_hour == b.exit_hour and (a.manage is None) == (b.manage is None))


def check(builder, sym, tf, params, seed=0, ks=5):
    df = load(sym, tf)
    full = S.BUILDERS[builder](df, **params)
    rng = random.Random(seed)
    n = len(df)
    bad = 0
    for _ in range(ks):
        k = rng.randint(n // 3, n - 1)
        part = df.iloc[:k].reset_index(drop=True)
        part.attrs.update(df.attrs)
        cut = S.BUILDERS[builder](part, **params)
        for i in range(k):
            if not same(full[i], cut[i]):
                bad += 1
                if bad <= 3:
                    print(f"  MISMATCH {builder} {sym} {tf} k={k} i={i}: full={full[i]} cut={cut[i]}")
                break
    return bad


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "candidates"
    if which == "all":
        jobs = [(b, "DE40", "M30", {}) for b in S.BUILDERS if b not in ("d1_meanrev", "big_day")]
        jobs += [(b, "DE40", "D1", {}) for b in ("d1_meanrev", "big_day")]
    else:
        jobs = []
        for line in (HERE / "candidates.jsonl").read_text().splitlines():
            r = json.loads(line)
            jobs.append((r["builder"], r["symbol"], r["tf"], r["params"]))
    tot = 0
    for b, s, tf, p in jobs:
        bad = check(b, s, tf, p)
        tot += bad
        print(f"{b:<20} {s:<6} {tf:<4} {p} -> {'OK' if bad == 0 else f'{bad} MISMATCHES'}")
    print("total mismatches:", tot)
