"""Causality check: signals on bars < k must not change when rows >= k are removed.
Also checks manage() decisions do not depend on future rows."""
import numpy as np
import pytest
from research.prop import harness as H
from research.search.public_eas import strategies as S

CASES = [("macd_sample", {}), ("moving_average", {}), ("free_robot", {"pattern": "star", "osc": "stoch"}),
         ("free_robot", {"pattern": "hammer", "osc": "cci"}), ("free_robot", {"pattern": "soldiers", "osc": "mfi"}),
         ("spike_trader", {}), ("ichimoku_chikou", {}), ("weekly_breakout", {}),
         ("weekly_breakout", {"period": "D"}), ("bb_breakout", {}), ("picky_breakout", {}),
         ("persistent_anti", {}), ("turtle", {}), ("connors_rsi2", {}), ("alligator", {})]


def _key(e):
    return None if e is None else (e.side, round(e.sl, 6), None if e.tp is None else round(e.tp, 6), e.max_hold)


@pytest.mark.parametrize("name,params", CASES)
def test_causal(name, params):
    df = H.load("XAUUSD", "H4", split="is").iloc[:6000].copy()
    df.attrs.update(symbol="XAUUSD", tf="H4")
    full = S.BUILDERS[name](df, **params)
    for k in (2500, 4000, 5999):
        part_df = df.iloc[:k].copy(); part_df.attrs.update(df.attrs)
        part = S.BUILDERS[name](part_df, **params)
        assert [_key(e) for e in full[:k]] == [_key(e) for e in part], (name, k)
        # manage decisions on bars < k identical
        for i in range(k - 300, k):
            e = full[i]
            if e is not None and e.manage is not None:
                pe = part[i]
                pos = dict(side=e.side, entry=float(df.close.iloc[i]), sl=e.sl, bar=i)
                for j in range(i + 1, k):
                    a = e.manage(df, j, dict(pos)); b = pe.manage(part_df, j, dict(pos))
                    assert a == b, (name, i, j)
