import numpy as np
import pandas as pd
import pytest

from research.public_ea_replay import signals, simulate, rsi


def bars(n=300):
    close = 1.1 + .01 * np.sin(np.arange(n) / 12)
    return pd.DataFrame(dict(time=pd.date_range('2025-01-01', periods=n, freq='h'),
                             open=close, high=close+.001, low=close-.001, close=close))


@pytest.mark.parametrize('name', ['adjustable_ma', 'rsi', 'heiken_ashi'])
def test_signals_do_not_read_future(name):
    d = bars()
    pd.testing.assert_frame_equal(signals(d, name).iloc[:200], signals(d.iloc[:200], name))


def test_rsi_seed_flat_up_down():
    assert rsi(pd.Series(np.ones(30))).iloc[-1] == 50
    assert rsi(pd.Series(np.arange(30.))).iloc[-1] == 100
    assert rsi(pd.Series(-np.arange(30.))).iloc[-1] == 0


@pytest.mark.parametrize('side', [-1, 1])
def test_flat_price_roundtrip_pays_both_fills_and_commission(side):
    d = bars(4)
    d[['open', 'high', 'low', 'close']] = 1.1
    s = pd.DataFrame(dict(entry=[side, 0, 0, 0], exit_long=[False, True, False, False],
                          exit_short=[False, True, False, False]))
    result, trades = simulate(d, s, d.time.iloc[0], d.time.iloc[-1]+pd.Timedelta(hours=1))
    assert len(trades) == 1
    assert trades.iloc[0].entry_time == d.time.iloc[1]
    assert trades.iloc[0].exit_time == d.time.iloc[2]
    assert result['net'] == pytest.approx(-2.6)  # $1 spread + $.2 slip + $1.4 fee


def test_underwater_open_trade_flags_static_limit_even_if_it_recovers():
    d = bars(4)
    d[['open', 'high', 'low', 'close']] = 1.1
    d.loc[2, 'low'] = 1.03
    s = pd.DataFrame(dict(entry=[1, 0, 0, 0], exit_long=False, exit_short=False))
    result, trades = simulate(d, s, d.time.iloc[0], d.time.iloc[-1]+pd.Timedelta(hours=1))
    assert result['static_600_breached']
    assert result['net'] > -3
