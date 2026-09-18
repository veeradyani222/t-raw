import pandas as pd
import pytest

from research.gold_session_recheck import simulate


def candles():
    return pd.DataFrame(dict(time=pd.date_range('2026-01-01', periods=48, freq='h'),
                             open=2000., high=2001., low=1999., close=2000.))


def test_gold_time_exit_contract_and_percentage_commissions():
    d = candles()
    d.loc[36, ['open', 'high', 'low', 'close']] = [2010., 2011., 2009., 2010.]
    s, t = simulate(d, pd.Timestamp('2026-01-02'), pd.Timestamp('2026-01-03'))
    assert len(t) == 1
    trade = t.iloc[0]
    assert trade.reason == 'time'
    assert trade.exit_time - trade.entry_time == pd.Timedelta(hours=12)
    assert trade.entry == pytest.approx(2000.33)
    assert trade['exit'] == pytest.approx(2009.97)
    fees = (trade.entry + trade['exit']) * 100 * trade.lots * .000018
    assert trade.fees == pytest.approx(fees)
    assert trade.profit == pytest.approx((2009.97-2000.33)*100*trade.lots-fees)
    assert s['final_balance'] == pytest.approx(10000+trade.profit)


@pytest.mark.parametrize('gap', [False, True])
def test_stop_beats_timed_exit_and_gap_fills_at_open(gap):
    d = candles()
    d.loc[36, ['open', 'high', 'low', 'close']] = [1990. if gap else 2000., 2001., 1989., 2000.]
    _, t = simulate(d, pd.Timestamp('2026-01-02'), pd.Timestamp('2026-01-03'))
    trade = t.iloc[0]
    assert trade.reason == ('gap_sl' if gap else 'sl')
    assert trade['exit'] == pytest.approx((1990. if gap else 1996.)-.03)
    if not gap:
        assert -100 <= trade.profit < 0


def test_missing_midnight_candles_produces_no_trades():
    d = candles()
    d = d[d.time.dt.hour != 0].reset_index(drop=True)
    s, t = simulate(d, pd.Timestamp('2026-01-02'), pd.Timestamp('2026-01-03'))
    assert t.empty
    assert s['net'] == 0
    assert s['final_balance'] == 10000
