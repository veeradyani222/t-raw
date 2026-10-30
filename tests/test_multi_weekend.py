"""Crypto trades 24/7: the server day (broker midnight) rolls on Saturday
and Sunday too, the daily stop pins one weekend day only, and max_hold /
exit_hour count weekend bars exactly as research.prop.harness.simulate does.
Synthetic BTCUSD H1 bars across a weekend on the replay broker."""
import numpy as np
import pandas as pd
import pytest

from research.prop import harness as H
from trader import multi
from trader.multi import AccountGuard, StrategySpec
from research.prop.harness import Entry
from tests.fake_market import FakeMarket


def T(s):
    return pd.Timestamp(s)


# ----------------------------------------------------------------- guard
def test_server_day_rolls_on_saturday_and_sunday():
    g = AccountGuard()
    assert g.update(T("2026-11-06 23:50"), 10_000, 10_000) == ["new_day"]        # Friday
    assert g.update(T("2026-11-07 00:00"), 10_000, 10_000) == ["new_day"]        # Saturday
    assert g.day == "2026-11-07"
    assert g.update(T("2026-11-07 13:00"), 9_690, 10_000) == ["daily_stop", "scale_on"]
    assert g.blocked
    assert g.update(T("2026-11-07 23:59"), 9_950, 10_000) == ["scale_off"]       # same day: still blocked
    assert g.blocked
    ev = g.update(T("2026-11-08 00:00"), 9_950, 9_950)                           # Sunday is a new server day
    assert ev == ["new_day"] and not g.blocked and g.day_start_balance == 9_950
    assert g.update(T("2026-11-09 00:00"), 9_950, 9_950) == ["new_day"]          # Monday


def test_guard_clock_follows_the_symbol_that_still_ticks_at_the_weekend(tmp_path):
    class Mkt:
        ticks = {"EURUSD": T("2026-11-06 23:59"), "BTCUSD": T("2026-11-08 03:00")}
        def tick_time(self, s):
            return self.ticks[s]
        def account(self):
            return 10_000.0, 10_000.0
        def positions(self):
            return []
        def realized_since(self, t):
            return 0.0
    specs = [StrategySpec(0, "m", "f", {}, "EURUSD", "H1", 0.01), StrategySpec(1, "m", "f", {}, "BTCUSD", "H1", 0.01)]
    r = multi.MultiRunner(Mkt(), specs, {}, state_path=tmp_path / "s.json")
    assert r.server_time() == T("2026-11-08 03:00")
    assert r.check_guard() == ["new_day"] and r.guard.day == "2026-11-08"


# ----------------------------------------------------------------- weekend bars
def _btc_frame(n=192, p0=60_000.0, seed=3):
    """24/7 H1 bars from Thu 2026-11-05 00:00; gentle noise so a far stop never fills."""
    rng = np.random.default_rng(seed)
    t = pd.date_range("2026-11-05 00:00", periods=n, freq="h")
    close = p0 + np.cumsum(rng.normal(0, 20.0, n))
    open_ = np.r_[p0, close[:-1]]
    df = pd.DataFrame(dict(time=t, open=open_, high=np.maximum(open_, close) + 10, low=np.minimum(open_, close) - 10,
                           close=close, tick_volume=100, spread=2500))
    df["conv"] = 1.0
    df.attrs.update(symbol="BTCUSD", tf="H1", split="all", score_from=None)
    assert df["time"].dt.dayofweek.isin([5, 6]).sum() == 48, "two full weekend days expected"
    return df


def _signals(df, entry_time, **kw):
    """One long entry at `entry_time` with a stop far below (never hit)."""
    sig = [None] * len(df)
    i = int(np.flatnonzero(df["time"].to_numpy() == np.datetime64(pd.Timestamp(entry_time)))[0])
    sig[i] = Entry("long", float(df["close"].iloc[i]) - 5_000.0, None, **kw)
    return sig


def _replay(monkeypatch, df, sig, tmp_path, window=100):
    spec = StrategySpec(0, "tests.test_multi_weekend", "build_fixture", {}, "BTCUSD", "H1", 0.01)
    monkeypatch.setattr(StrategySpec, "build", lambda self, w: [sig[k] for k in _index_of(df, w)])
    start = int(np.flatnonzero(df["time"] == T("2026-11-06 12:00"))[0])   # Friday noon, flat
    mkt = FakeMarket({"BTCUSD": df}, "H1", start)
    runner = multi.MultiRunner(mkt, [spec], {}, state_path=tmp_path / "s.json", window=window,
                               guard=AccountGuard(scale_size=1.0))
    runner.warmup()
    runner.last_bar[("BTCUSD", "H1")] = mkt.now
    while mkt.i < len(df) - 1:
        mkt.advance()
        runner.poll()
    return runner, mkt


def _index_of(full, window):
    """Positions in the full frame of the window's bars (the window is a slice)."""
    k0 = int(np.flatnonzero(full["time"].to_numpy() == window["time"].to_numpy()[0])[0])
    return range(k0, k0 + len(window))


@pytest.mark.parametrize("entry_time,kw,expect_exit", [
    ("2026-11-06 22:00", dict(max_hold=3), "2026-11-07 01:00"),            # Fri 22:00 + 3 bars -> Sat 01:00
    ("2026-11-07 10:00", dict(exit_hour=3), "2026-11-08 03:00"),           # Sat entry, exits Sun 03:00
    ("2026-11-06 20:00", dict(exit_hour=20), "2026-11-07 20:00"),          # same hour next day (Saturday)
    ("2026-11-08 23:00", dict(max_hold=2), "2026-11-09 01:00"),            # Sun 23:00 -> Mon 01:00
])
def test_time_exits_count_weekend_bars_like_the_harness(monkeypatch, tmp_path, entry_time, kw, expect_exit):
    df = _btc_frame()
    sig = _signals(df, entry_time, **kw)
    ref = H.simulate(df, sig, risk=0.01)["trades"]
    assert len(ref) == 1 and ref.reason.iloc[0] == "time"
    assert pd.Timestamp(ref.exit_time.iloc[0]) == T(expect_exit)         # the harness itself counts weekend bars

    runner, mkt = _replay(monkeypatch, df, sig, tmp_path)
    opens = [e for e in runner.events if e["kind"] == "open"]
    closes = [e for e in runner.events if e["kind"] == "close"]
    assert len(opens) == 1 and pd.Timestamp(opens[0]["time"]) == T(entry_time)
    assert len(closes) == 1 and closes[0]["reason"] == "time"
    assert len(mkt.closes) == 1 and pd.Timestamp(mkt.closes[0]["time"]) == T(expect_exit)
    assert abs(mkt.closes[0]["pnl"] - float(ref.profit.iloc[0])) < 0.01


def test_a_weekend_daily_stop_closes_the_crypto_position_and_blocks_only_that_day(monkeypatch, tmp_path):
    df = _btc_frame()
    sig = _signals(df, "2026-11-06 22:00", max_hold=200)
    spec = StrategySpec(0, "tests.test_multi_weekend", "build_fixture", {}, "BTCUSD", "H1", 0.01)
    monkeypatch.setattr(StrategySpec, "build", lambda self, w: [sig[k] for k in _index_of(df, w)])
    start = int(np.flatnonzero(df["time"] == T("2026-11-06 12:00"))[0])
    mkt = FakeMarket({"BTCUSD": df}, "H1", start)
    runner = multi.MultiRunner(mkt, [spec], {}, state_path=tmp_path / "s.json", window=100,
                               guard=AccountGuard(scale_size=1.0))
    runner.warmup()
    runner.last_bar[("BTCUSD", "H1")] = mkt.now
    sat_noon = int(np.flatnonzero(df["time"] == T("2026-11-07 12:00"))[0])
    while mkt.i < sat_noon:
        mkt.advance()
        runner.poll()
    assert runner.states[0].open and runner.guard.day == "2026-11-07"
    mkt.balance -= 400.0                                   # a loss booked on Saturday's server day
    runner.poll()
    kinds = [e["kind"] for e in runner.events]
    assert "daily_stop" in kinds and not runner.states[0].open and runner.guard.blocked
    assert mkt.closes[-1]["reason"] == "daily_stop"
    while mkt.i < len(df) - 1 and runner.guard.day == "2026-11-07":
        mkt.advance()
        runner.poll()
    assert runner.guard.day == "2026-11-08" and not runner.guard.blocked      # Sunday: trading allowed again
