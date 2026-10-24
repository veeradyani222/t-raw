"""The three risk rules on top of the account guard (docs/2026-10-25-overlay-
lab-results.md): drawdown scaling with hysteresis, the monthly loss stop with
its month boundary, and the minimum stop distance used for sizing. Plus the
symbol-spec table that a fresh clone must find in config/."""
import json

import pandas as pd
import pytest

from trader import multi
from trader.multi import AccountGuard, LivePos


def T(s):
    return pd.Timestamp(s)


# ----------------------------------------------------------------- scaler
def test_scaler_halves_below_9700_and_releases_only_above_9900():
    g = AccountGuard()
    g.update(T("2026-11-02 00:05"), 9_900, 9_900)
    assert g.size_factor == 1.0
    assert g.update(T("2026-11-02 09:00"), 9_710, 9_900) == []          # not yet
    assert g.update(T("2026-11-02 09:10"), 9_699, 9_900) == ["scale_on"]
    assert g.size_factor == 0.5
    assert g.update(T("2026-11-02 12:00"), 9_850, 9_900) == []          # between the bands: still half
    assert g.size_factor == 0.5
    assert g.update(T("2026-11-02 13:00"), 9_900, 9_900) == []          # must be ABOVE 9,900
    assert g.update(T("2026-11-02 14:00"), 9_901, 9_900) == ["scale_off"]
    assert g.size_factor == 1.0
    assert g.update(T("2026-11-02 15:00"), 9_750, 9_900) == []          # no re-trigger until below 9,700
    assert g.update(T("2026-11-03 00:00"), 9_690, 9_900) == ["new_day", "scale_on"]


def test_scaler_can_be_switched_off():
    g = AccountGuard(scale_size=1.0)
    g.update(T("2026-11-02 00:05"), 9_500, 9_500)
    assert g.size_factor == 1.0 and not g.scaled


def test_scaler_state_survives_a_restart():
    g = AccountGuard()
    g.update(T("2026-11-02 00:05"), 9_650, 9_700)
    g2 = AccountGuard.from_dict(g.to_dict())
    assert g2.scaled and g2.size_factor == 0.5


# ----------------------------------------------------------------- monthly stop
def test_monthly_stop_measures_from_previous_month_close_and_resets_next_month():
    g = AccountGuard(scale_size=1.0)                 # scaler off: this test is about the month
    g.update(T("2026-11-02 00:05"), 10_000, 10_000)
    assert g.month == "2026-11" and g.month_start_balance == 10_000
    assert g.update(T("2026-11-10 10:00"), 9_520, 9_600) == ["new_day"]  # -480 incl. floating
    assert g.update(T("2026-11-10 10:10"), 9_500, 9_600) == ["month_stop"]
    assert g.month_blocked and g.blocked and g.may_open()[0] is False
    assert "monthly" in g.may_open()[1]
    assert g.mtd(9_500) == -500
    assert g.update(T("2026-11-20 10:00"), 9_900, 9_900) == ["new_day"]  # recovery does not unblock
    assert g.month_blocked
    ev = g.update(T("2026-12-01 00:00"), 9_900, 9_900)
    assert ev == ["new_day", "month_released"]
    assert not g.month_blocked and g.may_open() == (True, "")
    assert g.month == "2026-12" and g.month_start_balance == 9_900
    assert g.update(T("2026-12-05 10:00"), 9_400, 9_500) == ["new_day", "month_stop"]   # fresh -500 from the new anchor


def test_month_start_balance_can_be_supplied_on_restart():
    g = AccountGuard(scale_size=1.0)
    # restarted on the 15th with balance 9,700 after -200 already realised this month
    g.update(T("2026-11-15 12:00"), 9_700, 9_700, day_start_balance=9_650, month_start_balance=9_900)
    assert g.month_start_balance == 9_900
    assert g.update(T("2026-11-15 12:01"), 9_400, 9_700) == ["month_stop"]   # -250 on the day, -500 on the month


def test_monthly_stop_can_be_switched_off():
    g = AccountGuard(monthly_stop=0.0, scale_size=1.0)
    g.update(T("2026-11-02 00:05"), 10_000, 10_000)
    ev = g.update(T("2026-11-02 10:00"), 9_000, 9_500)
    assert "month_stop" not in ev and "blown" in ev and not g.month_blocked


class StubMarket:
    def __init__(self, equity=10_000.0, balance=10_000.0, realized_month=0.0, daily=None):
        self.equity, self.balance = equity, balance
        self.realized_month = realized_month
        self.daily = daily
        self.book = {1: LivePos(1, "XAUUSD", 500_001, "long", 0.1, 4000, 3990, 0, T("2026-11-01 01:00")),
                     2: LivePos(2, "EURUSD", 500_020, "short", 0.2, 1.1, 1.11, 0, T("2026-11-01 01:00"))}
        self.closed = []
        self.rate_calls = []

    def rates(self, symbol, tf, count):
        self.rate_calls.append((symbol, tf, count))
        return self.daily if tf == "D1" else pd.DataFrame()
    def tick_time(self, symbol):
        return T("2026-11-10 10:00")
    def account(self):
        return self.equity, self.balance
    def positions(self):
        return list(self.book.values())
    def open(self, *a, **k):
        raise AssertionError("no entries expected")
    def close(self, pos, comment):
        self.closed.append(pos.ticket)
        del self.book[pos.ticket]
        return 0.0
    def modify(self, pos, sl, tp):
        pass
    def cancel_pending(self):
        return 0
    def realized_since(self, t):
        return self.realized_month if t.day == 1 else 0.0


def test_runner_monthly_stop_leaves_open_trades_alone_and_alerts(tmp_path):
    mkt = StubMarket(equity=9_650.0, balance=9_700.0, realized_month=-300.0)
    alerts = []
    r = multi.MultiRunner(mkt, multi.load_mix()[:1], {}, alert=alerts.append, state_path=tmp_path / "s.json")
    # month-start balance = 9,700 - (-300) = 10,000; equity 9,650 -> -350: fine, but below 9,700 -> half size
    assert r.check_guard(T("2026-11-10 10:00")) == ["new_day", "scale_on"]
    assert r.guard.month_start_balance == 10_000 and r.guard.size_factor == 0.5
    assert any("SIZE CUT" in a for a in alerts)
    mkt.equity = 9_480.0                                     # -520 on the month
    assert r.check_guard(T("2026-11-10 10:10")) == ["month_stop"]
    assert mkt.closed == [] and len(mkt.book) == 2            # open trades untouched
    assert r.guard.may_open()[0] is False and "monthly" in r.guard.may_open()[1]
    assert any("MONTHLY STOP" in a for a in alerts)
    assert any("month block ON" in ln for ln in r.status_lines())
    # survives a restart, and is released by the next server month
    r2 = multi.MultiRunner(StubMarket(equity=9_480.0, balance=9_700.0), multi.load_mix()[:1], {},
                           alert=alerts.append, state_path=tmp_path / "s.json")
    assert r2.guard.month_blocked
    ev = r2.check_guard(T("2026-12-01 00:00"))
    assert "month_released" in ev and r2.guard.may_open()[0] is True
    assert any("released" in a for a in alerts)


# ----------------------------------------------------------------- minimum sizing stop
def test_min_stop_math_gold():
    # gold long at 4000 with a $2 stop; ADR20 = 50 -> sizing distance 0.15*50 = 7.5
    plain = multi.size_trade("XAUUSD", "long", 4000.0, 3998.0, None, 30.0, 1.0, 0.01)
    sized = multi.size_trade("XAUUSD", "long", 4000.0, 3998.0, None, 30.0, 1.0, 0.01, min_stop_dist=7.5)
    entry = 4000.0 + 0.30 + 0.01                       # close + spread floor + slip
    stop = entry - 3998.0
    assert not plain["resized"] and sized["resized"]
    assert sized["stop_dist"] == pytest.approx(stop) and sized["size_dist"] == 7.5
    import math
    want = min(round(math.floor(100.0 / ((7.5 + 0.01) * 100 + 14.0) / 0.01) * 0.01, 2), 50.0)
    assert sized["lots"] == want and sized["lots"] < plain["lots"]
    # the real stop still carries the (smaller) dollar risk
    assert sized["risk_usd"] == pytest.approx(sized["lots"] * ((stop + 0.01) * 100 + 14.0))
    assert sized["risk_usd"] < 100.0
    # a normal stop is not touched
    wide = multi.size_trade("XAUUSD", "long", 4000.0, 3980.0, None, 30.0, 1.0, 0.01, min_stop_dist=7.5)
    assert not wide["resized"] and wide["lots"] == multi.size_trade("XAUUSD", "long", 4000.0, 3980.0, None, 30.0, 1.0, 0.01)["lots"]


def test_min_stop_math_index():
    # the DAX turn-of-month case: 9.9-point stop at 1.25% risk; ADR20 = 240 -> sizing distance 36
    plain = multi.size_trade("DE40", "long", 19400.0, 19390.1, None, 150.0, 1.0, 0.0125)
    sized = multi.size_trade("DE40", "long", 19400.0, 19390.1, None, 150.0, 1.0, 0.0125, min_stop_dist=36.0)
    assert plain["lots"] > 10 and sized["resized"]
    assert sized["lots"] == pytest.approx(3.4)         # 125 / (36.1 * 1) floored to 0.1 lots... per contract 1
    assert sized["risk_usd"] < plain["risk_usd"]


def test_average_daily_range_needs_history():
    d = pd.DataFrame({"high": [10.0] * 20, "low": [7.0] * 20})
    assert multi.average_daily_range(d) == 3.0
    assert multi.average_daily_range(d.head(5), 20) is None
    assert multi.average_daily_range(d.head(10), 20) == 3.0
    d2 = pd.DataFrame({"high": [10.0] * 30, "low": [7.0] * 10 + [9.0] * 20})
    assert multi.average_daily_range(d2) == 1.0        # only the last 20 count


def test_runner_min_stop_uses_broker_daily_bars_and_caches_per_day(tmp_path):
    daily = pd.DataFrame({"time": pd.date_range("2026-10-01", periods=20, freq="D"),
                          "open": 1.0, "high": 1.0100, "low": 1.0000, "close": 1.0,
                          "tick_volume": 1, "spread": 1})
    mkt = StubMarket(daily=daily)
    r = multi.MultiRunner(mkt, multi.load_mix()[:1], {}, state_path=tmp_path / "s.json")
    r.check_guard(T("2026-11-10 10:00"))
    assert r.min_stop_dist("EURUSD") == pytest.approx(0.15 * 0.01)
    r.min_stop_dist("EURUSD")
    assert len([c for c in mkt.rate_calls if c[1] == "D1"]) == 1          # cached for the day
    r.check_guard(T("2026-11-11 10:00"))
    r.min_stop_dist("EURUSD")
    assert len([c for c in mkt.rate_calls if c[1] == "D1"]) == 2          # refreshed next day
    off = multi.MultiRunner(mkt, multi.load_mix()[:1], {}, state_path=tmp_path / "o.json", min_stop_k=0.0)
    assert off.min_stop_dist("EURUSD") == 0.0
    short = multi.MultiRunner(StubMarket(daily=daily.head(3)), multi.load_mix()[:1], {}, state_path=tmp_path / "t.json")
    short.check_guard(T("2026-11-10 10:00"))
    assert short.min_stop_dist("EURUSD") == 0.0                             # too little history: rule off


# ----------------------------------------------------------------- symbol specs
def test_symbol_specs_prefer_config_then_fallback_then_refuse(tmp_path):
    cfg, data = tmp_path / "config.json", tmp_path / "data.json"
    data.write_text(json.dumps({"XAUUSD": {"contract": 100.0}}))
    assert multi.load_symbol_specs((cfg, data))["XAUUSD"]["contract"] == 100.0
    cfg.write_text(json.dumps({"XAUUSD": {"contract": 100.0, "point": 0.01}}))
    assert "point" in multi.load_symbol_specs((cfg, data))["XAUUSD"]
    with pytest.raises(FileNotFoundError, match="symbol_specs.json"):
        multi.load_symbol_specs((tmp_path / "nope.json", tmp_path / "nope2.json"))


def test_tracked_specs_match_the_research_table():
    cfg = json.loads((multi.ROOT / "config" / "symbol_specs.json").read_text())
    assert len(cfg) >= 23 and all(k in cfg for k in ("XAUUSD", "DE40", "EURJPY", "US500"))
    research = multi.ROOT / "data" / "search" / "symbol_specs.json"
    if research.exists():
        assert json.loads(research.read_text()) == cfg
