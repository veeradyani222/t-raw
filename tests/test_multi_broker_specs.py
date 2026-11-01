"""Research lots -> broker lots when the broker's contract differs (FundedNext indices are
10 units per lot, the research sized on 1), and the demo lock's allow-list."""
from types import SimpleNamespace

import MetaTrader5 as mt5
import pytest

from trader import multi
from trader.broker_mt5 import MT5Error, assert_demo


def test_same_contract_keeps_the_lots():
    assert multi.broker_lots("XAUUSD", 0.37, dict(contract=100.0, vol_min=0.01, vol_step=0.01)) == 0.37


def test_bigger_broker_contract_divides_and_rounds_down():
    # US500 research contract 1: 0.39 research lots = 0.39 index units -> 0.03 FundedNext lots (10 units each)
    assert multi.broker_lots("US500", 0.39, dict(contract=10.0, vol_min=0.01, vol_step=0.01)) == 0.03


def test_below_the_broker_minimum_is_skipped():
    assert multi.broker_lots("US500", 0.05, dict(contract=10.0, vol_min=0.01, vol_step=0.01)) is None


def test_no_broker_spec_trades_research_lots():
    assert multi.broker_lots("US500", 0.39, {}) == 0.39


def _acct(login, mode):
    return SimpleNamespace(login=login, trade_mode=mode)


def test_demo_always_passes(monkeypatch):
    monkeypatch.delenv("MULTI_ALLOW_REAL_LOGINS", raising=False)
    assert_demo(_acct(1, mt5.ACCOUNT_TRADE_MODE_DEMO))


def test_real_account_refused_unless_listed(monkeypatch):
    monkeypatch.delenv("MULTI_ALLOW_REAL_LOGINS", raising=False)
    with pytest.raises(MT5Error, match="NOT a demo"):
        assert_demo(_acct(12118056, mt5.ACCOUNT_TRADE_MODE_REAL))
    monkeypatch.setenv("MULTI_ALLOW_REAL_LOGINS", "999, 12118056")
    assert_demo(_acct(12118056, mt5.ACCOUNT_TRADE_MODE_REAL))
    with pytest.raises(MT5Error):
        assert_demo(_acct(555, mt5.ACCOUNT_TRADE_MODE_REAL))


def test_open_risk_follows_the_stop():
    st = multi.StratState(ticket=1, side="long", entry=100.0, sl=90.0, sl0=90.0, lots=1.0, risk_usd=50.0)
    assert multi.open_risk(st) == 50.0
    st.sl = 95.0
    assert multi.open_risk(st) == 25.0
    st.sl = 101.0                                     # trailed past the entry: nothing at risk
    assert multi.open_risk(st) == 0.0


def test_open_risk_cap_from_env(monkeypatch):
    monkeypatch.setenv("MULTI_ACCOUNT_SIZE", "5000")
    monkeypatch.delenv("MULTI_MAX_OPEN_RISK_PCT", raising=False)
    assert multi.max_open_risk() is None
    monkeypatch.setenv("MULTI_MAX_OPEN_RISK_PCT", "3")
    assert multi.max_open_risk() == 150.0
