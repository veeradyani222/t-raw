"""The rails and trade sizing follow the account size and the firm's limits from env."""
import pytest

from trader import multi


@pytest.mark.parametrize("size,dpct,mpct,stop,floor,low,high", [
    (None, None, None, 300, 9_300, 9_700, 9_900),          # default = $10K Stellar Lite (old constants)
    (5_000, 4, 8, 150, 4_650, 4_850, 4_950),               # $5K Stellar Lite
    (6_000, 5, 10, 225, 5_475, 5_775, 5_925),              # $6K Stellar 2-Step
])
def test_rails_follow_the_account(monkeypatch, size, dpct, mpct, stop, floor, low, high):
    for k, v in (("MULTI_ACCOUNT_SIZE", size), ("MULTI_DAILY_LIMIT_PCT", dpct), ("MULTI_MAX_LOSS_PCT", mpct)):
        monkeypatch.delenv(k, raising=False) if v is None else monkeypatch.setenv(k, str(v))
    g = multi.AccountGuard()
    assert (g.daily_stop, g.floor, g.scale_low, g.scale_high) == (stop, floor, low, high)
    if size is None:
        assert (g.daily_stop, g.floor, g.scale_low, g.scale_high) == (multi.DAILY_STOP, multi.FLOOR, multi.SCALE_LOW, multi.SCALE_HIGH)


def test_trade_risk_is_a_share_of_the_account(monkeypatch):
    monkeypatch.delenv("MULTI_ACCOUNT_SIZE", raising=False)
    big = multi.size_trade("EURUSD", "long", 1.10000, 1.09000, None, 10.0, 1.0, 0.01)
    monkeypatch.setenv("MULTI_ACCOUNT_SIZE", "5000")
    small = multi.size_trade("EURUSD", "long", 1.10000, 1.09000, None, 10.0, 1.0, 0.01)
    assert big["risk_usd"] <= 100 and small["risk_usd"] <= 50 and small["lots"] < big["lots"]


def test_saved_state_never_overrides_the_current_limits(monkeypatch):
    monkeypatch.setenv("MULTI_ACCOUNT_SIZE", "5000")
    g = multi.AccountGuard.from_dict(dict(daily_stop=300.0, floor=9_300.0, scale_low=9_700.0, day="2026-11-02", blown=False))
    assert g.daily_stop == 150 and g.floor == 4_650 and g.day == "2026-11-02"
