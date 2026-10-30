"""Look-ahead check: build(df) vs build(df.iloc[:k]) for random k; every
Entry at index < k must be identical (side/sl/tp/max_hold/exit_hour).
    python -m research.search3.commodity_fx.check_causal [fn SYM TF json-params]
With no args: smoke-runs every builder on AUDNZD H1 with defaults."""
import json, sys, time, random
import numpy as np
from research.search3.commodity_fx import run as R      # applies patches
from research.search3.commodity_fx import strategies as S
from research.prop import harness as H


def key(e):
    return None if e is None else (e.side, round(e.sl, 7), None if e.tp is None else round(e.tp, 7), e.max_hold, e.exit_hour)


def causal(fn, sym, tf, params, ks=5, seed=0):
    df = R.load(sym, tf)
    full = getattr(S, "build_" + fn)(df, **params)
    rng = random.Random(seed)
    n = len(df)
    bad = 0
    for k in [rng.randint(n // 3, n - 5) for _ in range(ks)]:
        sub = df.iloc[:k].copy().reset_index(drop=True)
        sub.attrs.update(df.attrs)
        part = getattr(S, "build_" + fn)(sub, **params)
        diff = [i for i in range(k) if key(full[i]) != key(part[i])]
        if diff:
            bad += 1
            print(f"  LOOKAHEAD {fn} {sym} {tf} k={k}: {len(diff)} diffs, first {diff[:3]}")
    return bad == 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        fn, sym, tf = sys.argv[1:4]
        params = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        print("causal_ok", causal(fn, sym, tf, params))
    else:
        for fn in [n[6:] for n in dir(S) if n.startswith("build_")]:
            t0 = time.time()
            ok = causal(fn, "AUDNZD", "H1", {}, ks=2)
            df = R.load("AUDNZD", "H1")
            sigs = getattr(S, "build_" + fn)(df)
            t1 = time.time()
            s = H.score(df, sigs, name=fn)
            print(f"{fn:<16} causal={ok} nsig={sum(x is not None for x in sigs):5d} build {t1-t0:.1f}s score {time.time()-t1:.1f}s | {H.summary_line(s)}", flush=True)
