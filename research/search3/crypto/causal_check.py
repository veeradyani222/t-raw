"""Look-ahead check: build(df) vs build(df.iloc[:k]) (attrs re-attached) for 5 random k;
every Entry at index < k must be identical (side, sl, tp, max_hold, exit_hour).
usage: python -m research.search3.crypto.causal_check [fn=params-json ...]  (default: all builds, defaults)"""
import json
import os
import sys

os.environ["PROP_OOS"] = "1"
import numpy as np

from research.prop import harness as H
from research.search3.crypto import costs, strategies as S

costs.apply()


def same(a, b):
    if (a is None) != (b is None):
        return False
    if a is None:
        return True
    return (a.side == b.side and abs(a.sl - b.sl) < 1e-9 and
            ((a.tp is None and b.tp is None) or (a.tp is not None and b.tp is not None and abs(a.tp - b.tp) < 1e-9))
            and a.max_hold == b.max_hold and a.exit_hour == b.exit_hour)


def check(fn, params, sym="ETHUSD", tf="H1", seed=0):
    df = H.load(sym, tf, split="oos")
    full = getattr(S, fn)(df, **params)
    rng = np.random.default_rng(seed)
    ks = sorted(rng.integers(len(df) // 3, len(df) - 10, size=5))
    bad = 0
    for k in ks:
        part = df.iloc[:k].copy(); part.attrs.update(df.attrs)
        sub = getattr(S, fn)(part, **params)
        for i in range(k):
            if not same(full[i], sub[i]):
                bad += 1
    return bad, ks, sum(x is not None for x in full)


if __name__ == "__main__":
    args = sys.argv[1:]
    todo = []
    if args:
        for a in args:
            fn, _, p = a.partition("=")
            todo.append((fn, json.loads(p) if p else {}))
    else:
        todo = [(n, {}) for n in dir(S) if n.startswith("build_")]
    for fn, p in todo:
        for sym, tf in (("ETHUSD", "H1"), ("BTCUSD", "D1")):
            bad, ks, n = check(fn, p, sym, tf)
            print(f"{fn:<22}{sym:<8}{tf:<4}{p} signals={n} k={ks} mismatches={bad}", flush=True)
