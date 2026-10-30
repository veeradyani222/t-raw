"""Look-ahead check: build(df) vs build(df.iloc[:k]) for 5 random k per
(builder, params, symbol, tf). Every Entry at index < k must be identical
(side, sl, tp, max_hold, exit_hour, meta). Usage:

    python research/search3/majors/causal_check.py            # defaults, all builders
    python research/search3/majors/causal_check.py cands.json # [{idea, symbol, tf, params}, ...]
"""
import json
import os
import random
import sys

os.environ["PROP_OOS"] = "1"
sys.path.insert(0, ".")
from research.prop import harness as H               # noqa: E402
from research.search3.majors import strategies as S  # noqa: E402


def same(a, b):
    if a is None or b is None:
        return a is b
    return (a.side == b.side and a.sl == b.sl and a.tp == b.tp and a.max_hold == b.max_hold
            and a.exit_hour == b.exit_hour and a.meta == b.meta
            and (a.manage is None) == (b.manage is None))


def check(idea, symbol, tf, params, seed=0, ks=5):
    df = H.load(symbol, tf, split="oos")
    full = S.BUILDERS[idea](df, **params)
    rng = random.Random(seed)
    n = len(df)
    bad = 0
    for k in [rng.randint(n // 4, n - 1) for _ in range(ks)]:
        part = df.iloc[:k].copy()
        part.attrs.update(df.attrs)
        sub = S.BUILDERS[idea](part, **params)
        diff = [i for i in range(k) if not same(full[i], sub[i])]
        if diff:
            bad += 1
            print(f"  MISMATCH {idea} {symbol} {tf} {params} k={k}: {len(diff)} bars, first {diff[:5]}")
    return bad


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cands = json.load(open(sys.argv[1]))
    else:
        cands = [dict(idea=i, symbol=s, tf=t, params={})
                 for i in S.BUILDERS for s, t in (("GBPCHF", "H1"), ("EURUSD", "M30"), ("EURCHF", "D1"))]
    total_bad = 0
    for c in cands:
        b = check(c["idea"], c["symbol"], c["tf"], c.get("params", {}))
        total_bad += b
        print(f"{'OK ' if not b else 'BAD'} {c['idea']} {c['symbol']} {c['tf']} {c.get('params', {})}", flush=True)
    print("TOTAL MISMATCHING CHECKS:", total_bad)
