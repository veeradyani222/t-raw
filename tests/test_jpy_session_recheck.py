import pandas as pd
import pytest

from research.jpy_session_recheck import simulate


@pytest.mark.parametrize("symbol", ["USDJPY", "AUDJPY"])
def test_twelve_hour_exit_converts_yen_profit_and_charges_fees_once(symbol):
    times = pd.date_range("2026-01-01", periods=48, freq="h")
    df = pd.DataFrame(dict(time=times, open=100., high=100.5, low=99.5,
                           close=100., fx=100., fx_previous=100.))
    # Signal on Jan2 06:00; time exit on Jan2 18:00, twelve bars later.
    df.loc[42, ["open", "high", "low", "close", "fx"]] = [101., 101.5, 100.5, 101., 120.]
    summary, trades = simulate(df, symbol, 6, pd.Timestamp("2026-01-02"),
                               pd.Timestamp("2026-01-02 20:00"), spread_pips=1.)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t.reason == "time"
    assert t.exit_time-t.entry_time == pd.Timedelta(hours=12)
    rate = t["exit"] if symbol == "USDJPY" else 120.
    expected = (t["exit"]-t.entry)*100000*t.lots/rate - 7*t.lots
    assert t.profit == pytest.approx(expected)
    assert summary["final_balance"] == pytest.approx(10000+expected)
