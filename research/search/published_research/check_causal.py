"""Causality spot-check: signals built on df[:k+1] must equal the full-df
signal at bar k (for sampled k). python -m research.search.published_research.check_causal"""
import numpy as np
from research.prop import harness as H
from research.search.published_research import strategies as S

CASES = [("build_equity_calendar", "US30", dict(tom_days_before=0)),
         ("build_gold_calendar", "XAUUSD", dict(tom_days_before=0)),
         ("build_pre_fomc", "EURUSD", dict(side="long", sl_datr=1.0))]
for fn, sym, p in CASES:
    df = H.load(sym, "H1", split="is").iloc[-6000:].reset_index(drop=True)
    df.attrs.update(symbol=sym)
    full = getattr(S, fn)(df, **p)
    idx = [i for i, e in enumerate(full) if e is not None][-15:] + list(np.random.default_rng(0).integers(500, len(df), 15))
    bad = 0
    for k in idx:
        part = getattr(S, fn)(df.iloc[:k + 1].copy(), **p)[k]
        a, b = full[k], part
        if (a is None) != (b is None) or (a is not None and (a.side != b.side or abs(a.sl - b.sl) > 1e-9)):
            bad += 1
    print(fn, sym, "checked", len(idx), "mismatches", bad)
