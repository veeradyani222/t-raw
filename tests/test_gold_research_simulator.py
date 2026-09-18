"""Independent synthetic execution/risk checks for the offline research engine."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from research.gold_intraday.simulator import SimConfig, simulate


def bars(rows, times=None):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"],
                        index=pd.to_datetime(times) if times else
                        pd.date_range("2026-01-01 07:00", periods=len(rows), freq="5min"))


def signals(df, entries):
    out = pd.DataFrame({"side": 0, "sl": np.nan, "tp": np.nan, "max_hold": 100}, index=df.index)
    for i, side, sl, tp in entries:
        out.iloc[i] = [side, sl, tp, 100]
    return out


def run(df, entries, config=None, **kwargs):
    return simulate(df, signals(df, entries), start=kwargs.pop("start", df.index[0]), config=config, **kwargs)


PLAIN = SimConfig(spread_floor=0, commission_per_lot=0, slippage=0,
                  contract_size=1, min_lot=1, lot_step=1, max_lot=100,
                  risk=.0025)


def test_signal_fills_next_open_and_start_has_no_inherited_position():
    df = bars([(100, 100, 100, 100), (101, 101, 101, 101), (102, 102, 102, 102)])
    result = run(df, [(0, 1, 90, 120)], PLAIN)
    trade = result["trades"].iloc[0]
    assert trade.entry_time == df.index[1]
    assert trade.entry == 101
    assert trade.exit == 102
    assert run(df, [(0, 1, 90, 120)], PLAIN, start=df.index[1])["trades"].empty


@pytest.mark.parametrize("side, expected_entry, expected_exit", [(1, 100.33, 99.97), (-1, 99.97, 100.33)])
def test_bid_ask_slippage_fees_and_final_equity_reconcile(side, expected_entry, expected_exit):
    df = bars([(100, 100, 100, 100)] * 3)
    result = run(df, [(0, side, 90 if side == 1 else 110, 120 if side == 1 else 80)])
    trade = result["trades"].iloc[0]
    assert trade.entry == pytest.approx(expected_entry)
    assert trade.exit == pytest.approx(expected_exit)
    assert trade.commission == pytest.approx(trade.lots * 7)
    assert trade.profit == pytest.approx(-43 * trade.lots)
    assert result["summary"]["final_equity"] == pytest.approx(10000 + trade.profit)


def test_lots_include_execution_costs_and_cap_at_one():
    df = bars([(100, 100, 100, 100)] * 2)
    trade = run(df, [(0, 1, 99, 120)])["trades"].iloc[0]
    assert trade.lots == .17  # floor(25 / ((100.33 - 99 + .03)*100 + 7), .01)
    assert trade.lots * 143 <= 25


def test_gap_stop_fills_worse_open_and_sl_wins_intrabar_tie():
    df = bars([(100, 100, 100, 100), (100, 101, 99, 100), (85, 120, 80, 100)])
    trade = run(df, [(0, 1, 90, 110)], PLAIN)["trades"].iloc[0]
    assert trade.exit == 85
    assert trade.reason == "sl"
    df.iloc[2] = [100, 120, 80, 100]
    result = run(df, [(0, 1, 90, 110)], PLAIN)
    assert result["trades"].iloc[0].exit == 90
    assert result["summary"]["min_equity"] == 9980
    assert result["summary"]["peak_equity"] == 10002  # prior bar only, no post-stop rally


def test_guard_records_spread_gap_loss_despite_recovered_final_bar():
    # Spread jumps after entry; short mark incurs a loss beyond its original sized risk.
    df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100)])
    df["spread"] = [0, 0, 1100, 0]
    cfg = replace(PLAIN, risk=.1, daily_limit=.001, total_limit=.06)
    result = run(df, [(0, -1, 110, 90), (2, 1, 90, 110)], cfg)
    assert result["summary"]["internal_daily_halts"] == 1
    assert result["summary"]["worst_day_loss"] == 11
    assert len(result["trades"]) == 1
    assert result["trades"].iloc[0].reason == "sl"


def test_daily_reset_allows_entries_but_total_halt_is_permanent():
    df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (0, 0, 0, 0),
               (100, 100, 100, 100), (100, 100, 100, 100)],
              ["2026-01-01 07:00", "2026-01-01 07:05", "2026-01-01 07:10",
               "2026-01-02 07:00", "2026-01-02 07:05"])
    entries = [(0, 1, 90, 200), (3, 1, 90, 200)]
    cfg = replace(PLAIN, risk=.1, daily_limit=.03, total_limit=.5, firm_total_limit=.6)
    result = run(df, entries, cfg)
    assert result["summary"]["internal_daily_halts"] == 1
    assert len(result["trades"]) == 2
    result = run(df, entries, replace(cfg, total_limit=.06))
    assert len(result["trades"]) == 1
    assert result["summary"]["internal_total_halt"] == df.index[2]
    assert result["summary"]["firm_breach"]


def test_intraday_force_flat_and_day_gap_settlement_before_reset():
    df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (101, 101, 101, 101)],
              ["2026-01-01 18:50", "2026-01-01 18:55", "2026-01-01 20:00"])
    assert run(df, [(0, 1, 90, 120)], PLAIN)["trades"].iloc[0].reason == "flat_hour"
    df.index = pd.to_datetime(["2026-01-01 18:50", "2026-01-01 18:55", "2026-01-02 07:00"])
    result = run(df, [(0, 1, 90, 120)], PLAIN)
    assert result["trades"].iloc[0].reason == "day_gap"
    assert result["daily"].iloc[0].end_equity == 10002
    assert result["daily"].iloc[1].start_equity == 10002


def test_opposite_signal_closes_before_opening_and_observed_spread_blocks_entry():
    df = bars([(100, 100, 100, 100)] * 3)
    result = run(df, [(0, 1, 90, 110), (1, -1, 110, 90)], PLAIN)
    assert len(result["trades"]) == 2
    assert result["trades"].iloc[0].reason == "opposite"
    df["spread"] = [0, 61, 0]
    assert run(df, [(0, 1, 90, 110)], PLAIN)["trades"].empty


def test_tp_limit_has_no_gap_improvement_and_short_uses_ask():
    df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (80, 85, 75, 80)])
    result = run(df, [(0, -1, 110, 90)])
    assert result["trades"].iloc[0].exit == 90
    assert result["trades"].iloc[0].reason == "tp"


def test_empty_window_and_max_hold():
    df = bars([(100, 100, 100, 100)] * 4)
    sig = signals(df, [(0, 1, 90, 120)])
    sig.loc[df.index[0], "max_hold"] = 1
    result = simulate(df, sig, start=df.index[0], config=PLAIN)
    assert result["trades"].iloc[0].exit_time == df.index[2]
    assert result["trades"].iloc[0].reason == "max_hold"
    assert simulate(df, sig, start="2027-01-01", config=PLAIN)["summary"]["final_equity"] == 10000


def test_intrabar_loss_guard_uses_stop_excursion_despite_recovered_close():
    df = bars([(100, 100, 100, 100), (100, 100, 90, 100), (100, 100, 100, 100)])
    cfg = replace(PLAIN, risk=.1, daily_limit=.003)
    result = run(df, [(0, 1, 90, 120), (1, 1, 90, 120)], cfg)
    assert result["summary"]["internal_daily_halts"] == 1
    assert result["summary"]["worst_day_loss"] == 30
    assert result["summary"]["final_equity"] == 9970
    assert len(result["trades"]) == 1


def test_remaining_daily_and_total_headroom_bounds_lots_and_skips_below_minimum():
    df = bars([(100, 100, 100, 100)] * 2)
    cfg = replace(PLAIN, risk=.1, daily_limit=.003)
    assert run(df, [(0, 1, 90, 120)], cfg)["trades"].iloc[0].lots == 3
    cfg = replace(cfg, start_equity=9415)
    assert run(df, [(0, 1, 90, 120)], cfg)["trades"].iloc[0].lots == 1
    assert run(df, [(0, 1, 90, 120)], replace(cfg, start_equity=9405))["trades"].empty


def test_short_stop_triggers_on_ask_and_end_is_exclusive():
    df = bars([(100, 100, 100, 100), (100, 100.8, 100, 100), (90, 90, 90, 90)])
    result = run(df, [(0, -1, 101, 90)])
    assert result["trades"].iloc[0].reason == "sl"
    assert result["trades"].iloc[0].exit == pytest.approx(101.03)
    assert run(df, [(0, -1, 110, 90)], PLAIN, end=df.index[2])["trades"].iloc[0].exit == 100


def test_observed_spread_exceeds_floor_and_day_gap_signal_is_not_inherited():
    df = bars([(100, 100, 100, 100)] * 2)
    df["spread"] = 50
    assert run(df, [(0, 1, 90, 120)])["trades"].iloc[0].entry == pytest.approx(100.53)
    df.index = pd.to_datetime(["2026-01-01 18:55", "2026-01-02 07:00"])
    assert run(df, [(0, 1, 90, 120)])["trades"].empty


@pytest.mark.parametrize("fault", ["duplicate", "range", "nan", "negative_spread", "alignment"])
def test_invalid_data_is_rejected(fault):
    df = bars([(100, 100, 100, 100)] * 2)
    sig = signals(df, [])
    if fault == "duplicate":
        df.index = pd.DatetimeIndex([df.index[0]] * 2)
    elif fault == "range":
        df.iloc[0, 1] = 99
    elif fault == "nan":
        df.iloc[0, 0] = np.nan
    elif fault == "negative_spread":
        df["spread"] = -1
    else:
        sig.index = sig.index + pd.Timedelta(minutes=1)
    with pytest.raises(ValueError):
        simulate(df, sig, start=df.index[0])
