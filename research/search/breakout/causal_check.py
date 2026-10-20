"""Causality check: signals built on a truncated df must equal the prefix of
signals built on the full df (no look-ahead)."""
from research.prop import harness as H
from research.search.breakout import strategies as S

def same(a, b):
    if (a is None) != (b is None):
        return False
    return a is None or (a.side == b.side and abs(a.sl - b.sl) < 1e-9 and a.tp == b.tp)

df = H.load("XAUUSD", "H1", split="is")
cases = [("build_crabel", {"filt": "nr4"}), ("build_prev_week", {"trail_atr": 8.0}), ("build_session_orb", {}), ("build_pdhl", {}), ("build_pdhl", {"fade": True}),
         ("build_nr_break", {}), ("build_squeeze", {"trend": "d"}), ("build_donchian", {"trend": "d"})]
for fn, p in cases:
    full = getattr(S, fn)(df, **p)
    for cut in (20000, 35123, 50001):
        part = getattr(S, fn)(df.iloc[:cut].copy(), **p)
        bad = [i for i in range(cut) if not same(full[i], part[i])]
        print(fn, p, cut, "mismatches", len(bad), "signals", sum(x is not None for x in part))
