"""Every family must give the same signals on bars < k whether or not later bars exist."""
import os
os.environ.setdefault("PROP_OOS", "1")          # this test reads all years by design
import numpy as np
import pandas as pd
import pytest

from research.prop import harness as H
from research.search4.price_action import strategies as S


def _df(symbol="XAUUSD", tf="H1", n=3000):
    try:
        df = H.load(symbol, tf, split="all")
    except FileNotFoundError:
        pytest.skip(f"{symbol} {tf} data not present")
    df = df.iloc[-n:].reset_index(drop=True)
    df.attrs.update(symbol=symbol, tf=tf)
    return df


def _sig(e):
    return None if e is None else (e.side, round(e.sl, 6), None if e.tp is None else round(e.tp, 6), e.max_hold)


@pytest.mark.parametrize("fam,params", [(f, p) for f, ps in S.GRID.items() for p in ps])
def test_causal(fam, params):
    df = _df()
    fn = getattr(S, f"build_{fam}")
    full = [_sig(e) for e in fn(df, **params)]
    assert len(full) == len(df)
    assert sum(s is not None for s in full) > 0, "family never fires"
    for k in (900, 1777, 2500):
        part = df.iloc[:k].reset_index(drop=True); part.attrs.update(df.attrs)
        cut = [_sig(e) for e in fn(part, **params)]
        assert cut == full[:k], f"{fam} {params} differs before bar {k}"


def test_pivots_causal():
    df = _df()
    full = S.pivots(df, 3)
    part = df.iloc[:1500].reset_index(drop=True)
    cut = S.pivots(part, 3)
    for a, b in zip(full, cut):
        np.testing.assert_array_equal(np.asarray(a)[:1500], np.asarray(b))
