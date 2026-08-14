"""ORB v2: volume + structure confirmations, structure-derived TP, blocked
records, and the backtest CLI's trade log. All offline — synthetic candles."""
import pandas as pd
import pytest

import backtest
from trader.config import Config
from trader.sim import run_backtest
from trader.strategies import get_strategy
from trader.strategy import Blocked, Setup


def bars(closes, start="2026-01-05 01:00", spread=0.1, volumes=None):
    """Synthetic candles whose highs/lows track the CLOSE only (open may sit
    outside the range — harmless here). Keeping the extremes off the opens
    makes fractal swing locations exactly the local extremes of `closes`,
    which the structure tests rely on."""
    closes = pd.Series(closes, dtype=float)
    df = pd.DataFrame({
        "time": pd.date_range(start, periods=len(closes), freq="h"),
        "open": closes.shift(1).fillna(closes.iloc[0]),
        "high": closes + spread,
        "low": closes - spread,
        "close": closes,
    })
    if volumes is not None:
        df["tick_volume"] = volumes
    return df


def two_days(day1_closes, day2_closes, volumes=None):
    """Day 1 supplies swing history; day 2 is box + breakout. Day 1 starts at
    hour 2 — no bar at the session-start hour — so it can never form a box of
    its own and the session detector anchors on day 2."""
    d1 = bars(day1_closes, start="2026-01-05 02:00", volumes=None)
    d2 = bars(day2_closes, start="2026-01-06 01:00", volumes=None)
    df = pd.concat([d1, d2]).reset_index(drop=True)
    # Rebuild day-2 opens to chain from day 1's last close.
    df.loc[len(day1_closes), "open"] = day1_closes[-1]
    if volumes is not None:
        df["tick_volume"] = volumes
    return df


DOWNTREND = [106, 105, 104, 105, 106, 104, 103, 102, 103, 104, 103, 102]
UPTREND = [102, 103, 104, 103, 102, 104, 105, 106, 105, 104, 105, 106]


def cfg(**kw):
    base = dict(strategy="orb", orb_session_start_hour=1, orb_box_candles=3,
                orb_vol_filter=False, orb_structure_filter=False,
                orb_tp_mode="r_multiple")
    base.update(kw)
    return Config(**base)


# --- volume confirmation ---------------------------------------------------

def one_day(post_box, volumes=None):
    closes = [100.0, 100.3, 99.8] + list(post_box)
    return bars(closes, spread=0.2, volumes=volumes)


def test_volume_filter_blocks_thin_breakout():
    candles = one_day([100.1, 100.2, 101.5], volumes=[100, 100, 100, 100, 100, 40])
    result = get_strategy("orb").compute_signal(candles, cfg(orb_vol_filter=True))
    assert isinstance(result, Blocked)
    assert result.side == "long"
    assert "volume" in result.reason
    assert result.meta["vol_ratio"] == pytest.approx(0.4)


def test_volume_filter_passes_strong_breakout():
    candles = one_day([100.1, 100.2, 101.5], volumes=[100, 100, 100, 100, 100, 300])
    result = get_strategy("orb").compute_signal(candles, cfg(orb_vol_filter=True))
    assert isinstance(result, Setup)
    assert result.meta["vol_ratio"] == pytest.approx(3.0)


def test_volume_filter_auto_passes_without_volume_column():
    candles = one_day([100.1, 100.2, 101.5])
    result = get_strategy("orb").compute_signal(candles, cfg(orb_vol_filter=True))
    assert isinstance(result, Setup)


# --- structure confirmation ------------------------------------------------

def test_structure_filter_blocks_long_against_falling_lows():
    candles = two_days(DOWNTREND, [103.0, 103.2, 102.9, 104.0])
    result = get_strategy("orb").compute_signal(
        candles, cfg(orb_structure_filter=True))
    assert isinstance(result, Blocked)
    assert result.side == "long"
    assert "structure" in result.reason
    assert result.meta["structure"] == "LH/LL"


def test_structure_filter_passes_long_with_rising_lows():
    candles = two_days(UPTREND, [103.0, 103.2, 102.9, 104.0])
    result = get_strategy("orb").compute_signal(
        candles, cfg(orb_structure_filter=True))
    assert isinstance(result, Setup)
    assert result.side == "long"


def test_structure_filter_blocks_short_against_rising_highs():
    candles = two_days(UPTREND, [105.0, 104.8, 105.2, 103.5])
    result = get_strategy("orb").compute_signal(
        candles, cfg(orb_structure_filter=True))
    assert isinstance(result, Blocked)
    assert result.side == "short"


# --- structure-derived take profit ----------------------------------------

def test_structure_tp_targets_recent_swing_high():
    candles = two_days(UPTREND, [103.0, 103.2, 102.9, 104.0])
    setup = get_strategy("orb").compute_signal(candles, cfg(orb_tp_mode="structure"))
    assert isinstance(setup, Setup)
    # Most recent swing high far enough away is the day-1 peak at 106 + 0.1.
    assert setup.tp == pytest.approx(106.1)
    assert setup.meta["tp_source"] == "structure"
    assert setup.sl == pytest.approx(102.9 - 0.1)   # box low, unchanged


def test_structure_tp_falls_back_to_r_multiple():
    # Downtrend history: no swing high above entry -> R-multiple fallback.
    candles = two_days(DOWNTREND, [103.0, 103.2, 102.9, 108.0])
    setup = get_strategy("orb").compute_signal(candles, cfg(orb_tp_mode="structure"))
    assert isinstance(setup, Setup)
    risk = 108.0 - setup.sl
    assert setup.tp == pytest.approx(108.0 + 3.0 * risk)
    assert setup.meta["tp_source"] == "r_multiple"


# --- blocked signals reach the backtest log -------------------------------

def test_backtest_records_blocked_signals():
    candles = two_days(DOWNTREND, [103.0, 103.2, 102.9, 104.0, 104.1, 104.05])
    result = run_backtest(candles, cfg(orb_structure_filter=True,
                                       pip_size=0.1, spread_pips=0))
    assert result["trades"] == 0
    events = result["events"]
    assert not events.empty
    assert (events["kind"] == "blocked").any()
    assert events.iloc[0]["meta"]["structure"] == "LH/LL"


def test_trade_log_carries_meta_and_r_multiple():
    candles = two_days(UPTREND, [103.0, 103.2, 102.9, 104.0, 110.0, 110.5])
    result = run_backtest(candles, cfg(pip_size=0.1, spread_pips=0))
    trades = result["trade_log"]
    assert len(trades) == 1
    tr = trades.iloc[0]
    assert tr["reason"] == "tp"
    assert tr["box_high"] == pytest.approx(103.3)
    assert tr["bars_held"] >= 1
    assert tr["r_multiple"] == pytest.approx(3.0, abs=0.1)


# --- CLI -------------------------------------------------------------------

def test_cli_runs_from_csv_and_writes_trade_log(tmp_path, capsys):
    candles = two_days(UPTREND, [103.0, 103.2, 102.9, 104.0, 110.0, 110.5])
    data_file = tmp_path / "fixture.csv"
    candles.to_csv(data_file, index=False)

    backtest.main([
        "XAUUSD", "H1", "--from", "2026-01-05", "--to", "2026-01-07",
        "--data", str(data_file), "--log-dir", str(tmp_path / "logs"),
        "--tp-mode", "r_multiple", "--no-vol-filter", "--no-structure-filter",
        "--quiet",
    ])

    out = capsys.readouterr().out
    assert "trades:" in out and "final equity:" in out
    logs = list((tmp_path / "logs").glob("backtest-xauusd-h1-*.csv"))
    assert len(logs) == 1
    log_df = pd.read_csv(logs[0])
    assert list(log_df.columns) == backtest.LOG_COLUMNS
    trade_rows = log_df[log_df["kind"] == "trade"]
    assert len(trade_rows) == 1
    row = trade_rows.iloc[0]
    assert row["exit_reason"] == "tp"
    assert row["weekday"] == "Tuesday"           # 2026-01-06
    assert row["side"] == "long"
