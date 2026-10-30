"""Cost model patches for crypto symbols (harness has no entries for them).

Spread floors (price units): BTCUSD 25, ETHUSD 2, LTCUSD 0.25 (~0.3% of ~$85),
XRPUSD 0.0045 (~0.3% of ~$1.5), SOLUSD 0.5 (~0.3%), ADAUSD 0.002, BNBUSD 2.0, DOTUSD 0.015.
Slippage = 0.1 x _pip -> pips set to ~1/10 of the spread floor.
Crypto CFDs on FundedNext carry no per-lot commission -> added to H.INDICES.
XRPUSD vol_min is 100 lots, above simulate()'s default max_lots=50 -> max_lots lifted to 1e9
(risk sizing still caps lots by the stop distance).
"""
from functools import wraps

from research.prop import harness as H

SPREAD = {"BTCUSD": 25.0, "ETHUSD": 2.0, "LTCUSD": 0.25, "XRPUSD": 0.0045,
          "SOLUSD": 0.5, "ADAUSD": 0.002, "BNBUSD": 2.0, "DOTUSD": 0.015}
PIP = {k: v / 10 for k, v in SPREAD.items()}
_applied = False


def apply():
    global _applied
    if _applied:
        return
    H.SPREAD_FLOOR.update(SPREAD)
    H.INDICES.update(SPREAD.keys())
    _orig_pip = H._pip

    def _pip(symbol):
        return PIP[symbol] if symbol in PIP else _orig_pip(symbol)
    H._pip = _pip
    _orig_sim = H.simulate

    @wraps(_orig_sim)
    def simulate(df, signals, **kw):
        kw.setdefault("max_lots", 1e9)
        return _orig_sim(df, signals, **kw)
    H.simulate = simulate
    _applied = True
