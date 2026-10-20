"""Causality check: signals computed on df[:k] must equal signals on full df for bars < k."""
import numpy as np
from research.prop import harness as H
from research.search.gold_fix import strategies as S
CASES = [("build_bos", dict(htf=("1D", 50), atrp_min=0.6, tp_min_r=2.0), "M30"),
         ("build_bos", dict(trail_atr=3.0, tp_mode="none"), "H1"),
         ("build_donchian", dict(n_entry=20, n_exit=10), "H4"),
         ("build_session_break", dict(), "H1"),
         ("build_pullback", dict(), "H1")]
for fn, p, tf in CASES:
    df = H.load("XAUUSD", tf, split="is")
    full = getattr(S, fn)(df, **p)
    bad = 0
    for k in [len(df) // 3, len(df) // 2, len(df) - 500]:
        part = getattr(S, fn)(df.iloc[:k].reset_index(drop=True), **p)
        for i in range(k - 300, k):
            a, b = full[i], part[i]
            if (a is None) != (b is None) or (a is not None and (a.side != b.side or abs(a.sl - b.sl) > 1e-9)):
                bad += 1
    print(fn, tf, p, "mismatches", bad)
