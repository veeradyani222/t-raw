"""Every research.search3 strategy in the three round-3 mixes, judged for
the live runner (docs/2026-10-31-round3-live-readiness.md): importable, runs
on a 6000-bar window of synthetic bars at its timeframe with the columns
trader/multi.py supplies, reads nothing from data/ (no second symbol), and is
causal (the entry at bar i does not change when later bars are truncated or
altered). Strategies on config/live_skip.json must fail the data check (so
the skip list stays honest); all the others must pass everything."""
import importlib
import json

import numpy as np
import pandas as pd
import pytest

from research.prop import harness as H
from trader import multi

ROUND3 = {w: multi.ROOT / "docs" / "board" / f"portfolio-round3-{w}.json" for w in ("2y", "3y", "5y")}
CRYPTO = multi.CRYPTO
PRICE = {"XAUUSD": 2400.0, "XAGUSD": 28.0, "XPDUSD": 1000.0, "BTCUSD": 60000.0, "ETHUSD": 3000.0,
         "SOLUSD": 150.0, "XRPUSD": 0.55, "XTIUSD": 75.0, "XNGUSD": 2.5, "US500": 5200.0, "USTEC": 18000.0,
         "US30": 39000.0, "DE40": 18000.0, "FRA40": 7500.0, "AUS200": 7700.0, "CHINA50": 12000.0,
         "JPN225": 38000.0, "EURNOK": 11.5, "USDMXN": 17.5, "USDCNH": 7.2, "NZDUSD": 0.61, "EURUSD": 1.08,
         "GBPUSD": 1.27, "USDCHF": 0.9, "CHFJPY": 170.0}


def synth(symbol: str, tf: str, n: int = multi.WINDOW_BARS, seed: int = 1) -> pd.DataFrame:
    """A live-shaped window: server-time bars (weekdays only unless crypto),
    random-walk prices, the runner's columns and attrs."""
    rng = np.random.default_rng(seed)
    step = pd.Timedelta(minutes=multi.TF_MINUTES[tf])
    times, t = [], pd.Timestamp("2010-01-04 00:00")
    while len(times) < n:
        if symbol in CRYPTO or t.dayofweek < 5:
            times.append(t)
        t += step
    p0 = PRICE.get(symbol, 1.0)
    vol = 0.002 if tf != "D1" else 0.01
    close = p0 * np.exp(np.cumsum(rng.normal(0, vol, n)))
    open_ = np.r_[p0, close[:-1]] * np.exp(rng.normal(0, vol / 10, n))
    hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    df = pd.DataFrame(dict(time=pd.DatetimeIndex(times), open=open_, high=hi, low=lo, close=close,
                           tick_volume=rng.integers(100, 5000, n), spread=rng.integers(5, 30, n)))
    df["conv"] = 1.0
    df.attrs.update(symbol=symbol, tf=tf, split="live", score_from=None)
    return df


def _strategies():
    rows = {}
    for w, p in ROUND3.items():
        for m in json.loads(p.read_text())["mix"]:
            if m["module"].startswith("research.search3"):
                k = (m["module"], m["fn"], m["symbol"], m["tf"], json.dumps(m["params"], sort_keys=True))
                rows.setdefault(k, []).append(w)
    return [dict(module=k[0], fn=k[1], symbol=k[2], tf=k[3], params=json.loads(k[4]), mixes=v)
            for k, v in sorted(rows.items())]


STRATS = _strategies()
IDS = [f"{s['fn'].removeprefix('build_')}-{s['symbol']}-{s['tf']}" for s in STRATS]


def _key(e):
    return None if e is None else (e.side, round(float(e.sl), 10),
                                   None if e.tp is None else round(float(e.tp), 10), e.max_hold, e.exit_hour)


@pytest.fixture
def no_data_reads(monkeypatch, tmp_path):
    """Any read of data/ (csv or harness.load) raises."""
    def blocked(*a, **k):
        raise RuntimeError(f"data read blocked: {a[:1]} {k}")
    monkeypatch.setattr(pd, "read_csv", blocked)
    monkeypatch.setattr(H, "load", blocked)
    monkeypatch.setattr(H, "DATA", tmp_path / "no-data-here")


def test_the_three_mixes_hold_46_distinct_search3_strategies():
    assert len(STRATS) == 46
    assert {w for s in STRATS for w in s["mixes"]} == {"2y", "3y", "5y"}


@pytest.mark.parametrize("strat", STRATS, ids=IDS)
def test_search3_strategy_is_live_ready_or_on_the_skip_list(strat, no_data_reads):
    build = getattr(importlib.import_module(strat["module"]), strat["fn"])
    spec = multi.StrategySpec(0, strat["module"], strat["fn"], strat["params"], strat["symbol"], strat["tf"], 0.01)
    skipped = multi.skip_reasons([spec], multi.load_skip_list())
    df = synth(strat["symbol"], strat["tf"])
    if skipped:
        with pytest.raises(RuntimeError, match="data read blocked"):
            build(df, **strat["params"])
        return
    sig = build(df, **strat["params"])
    assert len(sig) == len(df), "signals must be one per bar"
    full = [_key(e) for e in sig]
    for e in sig:
        if e is not None:
            assert e.side in ("long", "short") and np.isfinite(e.sl), e
    n = len(df)
    # causal (1): truncating the window must not change earlier entries
    for k in (n - 1, n - 5, n - 60, n - 400):
        sub = df.iloc[:k].copy()
        sub.attrs.update(df.attrs)
        part = [_key(e) for e in build(sub, **strat["params"])]
        bad = [i for i in range(k) if part[i] != full[i]]
        assert not bad, f"look-ahead: truncating at {k} changed {len(bad)} entries (first at bar {bad[0]})"
    # causal (2): altering later bars must not change earlier entries
    k = n - 300
    alt = df.copy()
    alt.attrs.update(df.attrs)
    rng = np.random.default_rng(7)
    f = np.exp(rng.normal(0, 0.01, n - k))
    for c in ("open", "high", "low", "close"):
        alt.loc[k:, c] = alt.loc[k:, c].to_numpy() * f
    alt.loc[k:, "tick_volume"] = rng.integers(100, 5000, n - k)
    part = [_key(e) for e in build(alt, **strat["params"])]
    bad = [i for i in range(k) if part[i] != full[i]]
    assert not bad, f"look-ahead: altering bars after {k} changed {len(bad)} entries (first at bar {bad[0]})"


USD_PER = {"USD": 1.0, "EUR": 1.08, "AUD": 0.65, "JPY": 1 / 150, "CHF": 1.1, "NOK": 1 / 11, "MXN": 1 / 18, "CNH": 1 / 7.2}


def test_a_live_entry_from_each_runnable_group_can_be_sized():
    """size_trade on a representative 0.2%-stop signal per symbol at 1% risk,
    with a plausible USD conversion: the stop is funded (lots >= the symbol's
    minimum), i.e. the contract spec and cost patches are in place."""
    multi.apply_research_patches()
    seen = set()
    for strat in STRATS:
        sym = strat["symbol"]
        if sym in seen or multi.skip_reasons([multi.StrategySpec(0, strat["module"], strat["fn"], {}, sym,
                                                                 strat["tf"], 0.01)], multi.load_skip_list()):
            continue
        seen.add(sym)
        spec = multi.research_spec(sym)
        assert spec, f"{sym}: no contract spec in config/symbol_specs.json"
        p0 = PRICE[sym]
        conv = USD_PER[spec.get("profit_ccy", "USD")]
        sz = multi.size_trade(sym, "long", p0, p0 * 0.998, None, 10.0, conv, 0.01)
        assert sz is not None and sz["lots"] >= float(spec["vol_min"]), (sym, sz)
