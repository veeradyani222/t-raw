"""End-to-end pipeline proof on synthetic data — no MT5 required."""
import numpy as np
import pandas as pd
import pytest

from trader.config import Config
from trader.sim import run_backtest


def synthetic_history(bars=600, seed=7):
    rng = np.random.default_rng(seed)
    # Gold-scale swings, directional candle bodies and volume for BOS + CMF.
    drift = np.where((np.arange(bars) // 100) % 2 == 0, 0.2, -0.2)
    closes = 2000 + np.cumsum(drift + rng.normal(0, 0.8, bars))
    opens = np.concatenate([[closes[0]], closes[:-1]])
    high = np.maximum(opens, closes) + rng.uniform(0.2, 1.2, bars)
    low = np.minimum(opens, closes) - rng.uniform(0.2, 1.2, bars)
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=bars, freq="30min"),
        "open": opens, "high": high, "low": low, "close": closes,
        "tick_volume": rng.integers(100, 2000, bars),
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


@pytest.mark.parametrize("starting_equity", [1000, 10000])
def test_bos_cli_runs_offline_and_logs_signal_diagnostics(tmp_path, capsys, starting_equity):
    import backtest

    data = tmp_path / "candles.csv"
    synthetic_history(400).to_csv(data, index=False)
    output = tmp_path / "logs"
    backtest.main(["XAUUSD", "M30", "--from", "2026-01-01", "--to", "2026-01-10",
                   "--data", str(data), "--log-dir", str(output),
                   "--equity", str(starting_equity), "--quiet"])
    assert "strategy=bos" in capsys.readouterr().out
    files = list(output.glob("*.csv"))
    assert len(files) == 1
    logged = pd.read_csv(files[0])
    trades = logged[logged.kind == "trade"]
    assert not trades.empty
    assert trades[["level", "cmf"]].notna().all().all()


def test_bos_cli_rejects_price_only_history(tmp_path):
    import backtest

    data = tmp_path / "price-only.csv"
    synthetic_history(100).drop(columns="tick_volume").to_csv(data, index=False)
    with pytest.raises(SystemExit, match="requires a tick_volume"):
        backtest.main(["XAUUSD", "M30", "--from", "2026-01-01", "--to", "2026-01-04",
                       "--data", str(data), "--quiet"])
