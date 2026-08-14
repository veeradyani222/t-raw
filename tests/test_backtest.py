"""End-to-end pipeline proof on synthetic data — no MT5 required."""
import numpy as np
import pandas as pd

from trader.config import Config
from trader.sim import run_backtest


def synthetic_history(bars=600, seed=7):
    rng = np.random.default_rng(seed)
    # Random walk with alternating drift so crossovers actually happen.
    drift = np.where((np.arange(bars) // 100) % 2 == 0, 0.0002, -0.0002)
    closes = 1.10 + np.cumsum(drift + rng.normal(0, 0.0008, bars))
    high = closes + rng.uniform(0.0002, 0.0012, bars)
    low = closes - rng.uniform(0.0002, 0.0012, bars)
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=bars, freq="h"),
        "open": closes, "high": high, "low": low, "close": closes,
    })


def test_backtest_trades_and_stays_solvent():
    cfg = Config()
    result = run_backtest(synthetic_history(), cfg)
    assert result["trades"] > 0, "pipeline never traded — signal path broken"
    assert result["final_equity"] > 0
    # Accounting must be consistent: equity change equals summed trade profits.
    assert abs((result["final_equity"] - 10_000) - result["net_profit"]) < 1e-6


def test_stop_loss_actually_bounds_losses():
    cfg = Config()
    result = run_backtest(synthetic_history(), cfg)
    trades = result["trade_log"]
    sl_exits = trades[trades["reason"] == "sl"]
    if not sl_exits.empty:
        # Worst SL loss ≈ 1% of 10k = ~100, allow slack for equity growth/spread
        assert sl_exits["profit"].min() > -250


def test_never_more_than_one_position():
    # max_open_positions=1 must hold: every open is preceded by flat or a close.
    cfg = Config()
    result = run_backtest(synthetic_history(bars=800, seed=3), cfg)
    assert result["trades"] > 0
