import math

import pandas as pd
import pytest

from research import jpy_guarded_session as replay


def candles(days=3):
    return pd.DataFrame(dict(time=pd.date_range("2026-01-01", periods=24*days, freq="h"),
                             open=100., high=100.5, low=99.5, close=100.,
                             fx=100., fx_previous=100.))


def run(df, **kwargs):
    return replay.simulate(df, pd.Timestamp("2026-01-02"),
                           df.time.iloc[-1]+pd.Timedelta(hours=1), **kwargs)


@pytest.mark.parametrize("initial", [10000., 50000.])
def test_twelve_elapsed_hours_costs_sizing_and_conversion(initial):
    df = candles(2)
    df.loc[36, ["open", "high", "low", "close", "fx"]] = [101., 101.5, 100.5, 101., 120.]
    summary, trades = run(df, initial_balance=initial)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade.entry_time == df.time.iloc[24]
    assert trade.exit_time-trade.entry_time == pd.Timedelta(hours=12)
    assert trade.reason == "time"
    assert trade.entry == pytest.approx(100.026)
    assert trade.sl == pytest.approx(98.)
    expected_lots = math.floor(min(initial/10000, initial*.01/(2.027*1000+14))*100)/100
    assert trade.lots == expected_lots
    expected = (100.999-100.026)*100000*expected_lots/120-14*expected_lots
    assert trade.profit == pytest.approx(expected)
    assert trade.fx_used == 120
    assert trade.planned_risk == pytest.approx(expected_lots*2041)
    assert summary["net"] == pytest.approx(expected)
    assert summary["final_balance"] == pytest.approx(initial+expected)
    assert trade.equity_after == pytest.approx(initial+expected)


def test_signal_candle_low_cannot_stop_new_close_entry():
    df = candles(2)
    df.loc[24, "low"] = 80.
    _, trades = run(df)
    assert trades.iloc[0].reason == "time"


def test_full_risk_candidate_rejected_instead_of_shrunk_to_static_headroom():
    df = candles(14)
    for i in range(25, len(df), 24):
        df.loc[i, "low"] = 90.
    summary, trades = run(df)
    assert 4 <= len(trades) <= 8
    assert summary["blocked_static"] > 0
    assert summary["first_static_block"] > trades.exit_time.max()
    assert summary["final_balance"] > 9400
    assert summary["permanent_halt"] is None
    assert (trades.planned_risk <= trades.entry_balance*.01+1e-8).all()


def test_floating_guard_uses_conversion_and_exits_before_strategy_stop():
    df = candles(2)
    df.loc[25, ["low", "fx_previous"]] = [90., 20.]
    summary, trades = run(df)
    trade = trades.iloc[0]
    assert trade.reason == "daily_guard"
    assert trade["exit"] > trade.sl
    assert trade.fx_used == 20
    assert summary["final_balance"] == pytest.approx(9700.)
    assert summary["min_liquidation_equity"] == pytest.approx(9700.)
    assert summary["max_daily_loss"] == pytest.approx(300.)
    assert summary["internal_daily_breaches"] == 0
    assert summary["daily_guard_days"] == 1


def test_gap_fills_open_and_reports_internal_and_firm_breaches():
    df = candles(2)
    df.loc[25, ["open", "high", "low", "close"]] = [70., 100., 60., 100.]
    summary, trades = run(df)
    assert trades.iloc[0]["exit"] == pytest.approx(69.999)
    assert trades.iloc[0].reason.startswith("gap_")
    assert summary["final_balance"] < 9200
    assert summary["min_liquidation_equity"] == pytest.approx(summary["final_balance"])
    assert summary["permanent_halt"] == df.time.iloc[25]
    for key in ("internal_daily_breaches", "internal_static_breaches", "firm_daily_breaches", "firm_static_breaches"):
        assert summary[key] == 1


def test_daily_guard_resets_next_dataset_day_before_actions():
    df = candles(3)
    df.loc[25, ["open", "high", "low", "close"]] = [90., 100., 89., 100.]
    summary, trades = run(df)
    assert len(trades) == 2
    assert trades.iloc[1].entry_time == df.time.iloc[48]
    assert trades.iloc[1].entry_daily_headroom == pytest.approx(300.)
    assert summary["permanent_halt"] is None


def test_empty_window_has_stable_ledger_and_zero_metrics():
    df = candles(2)
    summary, trades = replay.simulate(df, pd.Timestamp("2027-01-01"), pd.Timestamp("2027-02-01"))
    assert trades.empty
    assert {"entry_time", "exit_time", "profit", "equity_after"} <= set(trades)
    assert summary["net"] == summary["trades"] == summary["closed_drawdown"] == 0
    assert summary["final_balance"] == summary["min_liquidation_equity"] == 10000


def test_strategy_stop_drawdown_ignores_post_exit_low_and_current_fx():
    df = candles(2)
    df.loc[25, ["low", "fx"]] = [10., 10000.]
    summary, trades = run(df)
    trade = trades.iloc[0]
    assert trade.reason == "sl"
    assert trade.fx_used == 100.
    assert trade.profit == pytest.approx(-trade.planned_risk)
    assert summary["min_liquidation_equity"] == pytest.approx(trade.equity_after)
    assert summary["max_daily_loss"] == pytest.approx(-trade.profit)
    assert summary["internal_daily_breaches"] == 0


def test_completed_trade_is_independent_of_future_candles():
    df = candles(3)
    _, prefix = run(df.iloc[:40].copy())
    df.loc[40:, ["open", "high", "low", "close", "fx"]] *= 2
    _, full = run(df)
    pd.testing.assert_series_equal(prefix.iloc[0], full.iloc[0])


def test_elapsed_time_exit_does_not_count_bars():
    df = candles(2).drop(index=[28, 29, 30]).reset_index(drop=True)
    _, trades = run(df)
    assert trades.iloc[0].exit_time == pd.Timestamp("2026-01-02 12:00")


def test_static_guard_takes_precedence_once_it_is_tighter():
    df = candles(7)
    for i in (25, 49, 73, 97):
        df.loc[i, "low"] = 90.
    df.loc[121, ["low", "fx_previous"]] = [90., 20.]
    summary, trades = run(df)
    assert trades.iloc[-1].reason == "static_guard"
    assert summary["final_balance"] == pytest.approx(9400.)
    assert summary["permanent_halt"] == df.time.iloc[121]
    assert summary["internal_static_breaches"] == 0
    assert summary["blocked_static"] > 0
