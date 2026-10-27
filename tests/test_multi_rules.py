"""Drawdown scaling on top of the account guard (docs/2026-10-25-overlay-
lab-results.md): half size below $9,700 with hysteresis up to $9,900, open
trades untouched, state across restarts. Plus the symbol-spec table that a
fresh clone must find in config/."""
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


def test_state_file_from_the_version_with_more_rules_still_loads(tmp_path):
    # the VM ran a build that stored month-anchor entries; unknown keys are ignored
    old = dict(guard=dict(daily_stop=300.0, floor=9300.0, day="2026-10-28", day_start_balance=9540.59,
                          blocked_day=None, blown=False, last_equity=9535.97, scale_low=9700.0,
                          scale_high=9900.0, scale_size=0.5, scaled=True, monthly_stop=500.0,
                          month="2026-10", month_start_balance=10000.0, month_anchor="history",
                          blocked_month=None),
               strategies={})
    p = tmp_path / "multi_state.json"
    p.write_text(json.dumps(old))
    r = multi.MultiRunner(StubMarket(), multi.load_mix()[:1], {}, state_path=p)
    assert r.guard.scaled and r.guard.day == "2026-10-28" and not r.guard.blown
    assert not hasattr(r.guard, "month")
    r.save_state()
    saved = json.loads(p.read_text())["guard"]
    assert "month" not in saved and "monthly_stop" not in saved and saved["scaled"] is True


class StubMarket:
    def __init__(self, equity=10_000.0, balance=10_000.0):
        self.equity, self.balance = equity, balance
        self.book = {1: LivePos(1, "XAUUSD", 500_001, "long", 0.1, 4000, 3990, 0, T("2026-11-01 01:00")),
                     2: LivePos(2, "EURUSD", 500_020, "short", 0.2, 1.1, 1.11, 0, T("2026-11-01 01:00"))}
        self.closed = []

    def rates(self, symbol, tf, count):
        return pd.DataFrame()
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
        return 0.0


def test_runner_scaler_leaves_open_trades_alone_alerts_and_shows_in_status(tmp_path):
    mkt = StubMarket(equity=9_650.0, balance=9_700.0)
    alerts = []
    r = multi.MultiRunner(mkt, multi.load_mix()[:1], {}, alert=alerts.append, state_path=tmp_path / "s.json")
    assert r.check_guard(T("2026-11-10 10:00")) == ["new_day", "scale_on"]
    assert r.guard.size_factor == 0.5
    assert mkt.closed == [] and len(mkt.book) == 2            # open trades untouched
    assert r.guard.may_open() == (True, "")                   # entries allowed, just smaller
    assert any("SIZE CUT" in a for a in alerts)
    assert any("size x0.5" in ln for ln in r.status_lines())
    r2 = multi.MultiRunner(StubMarket(equity=9_905.0, balance=9_700.0), multi.load_mix()[:1], {},
                           alert=alerts.append, state_path=tmp_path / "s.json")
    assert r2.guard.scaled                                    # survives a restart
    assert r2.check_guard(T("2026-11-10 10:05")) == ["scale_off"]
    assert any("FULL SIZE" in a for a in alerts)
    assert any("size x1" in ln for ln in r2.status_lines())


def test_half_size_halves_the_lots():
    full = multi.size_trade("XAUUSD", "long", 4000.0, 3980.0, None, 30.0, 1.0, 0.01)
    half = multi.size_trade("XAUUSD", "long", 4000.0, 3980.0, None, 30.0, 1.0, 0.01 * 0.5)
    assert half["lots"] == pytest.approx(full["lots"] / 2, abs=0.01)
    assert half["risk_usd"] == pytest.approx(full["risk_usd"] / 2, rel=0.03)


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
