"""Backtest the ORB strategy across timeframes and TP multiples on real MT5 data.

Usage: python run_orb_sweep.py M15 M30 H1        # timeframes to run
Pulls ~1 year of XAUUSD history per timeframe (cached to data/), runs
orb_tp_r in {2,3,4}, and appends every run to backtest-orb-1yr-results.csv.
"""
import logging
import sys
from pathlib import Path

import pandas as pd

from trader import broker_mt5
from trader.broker_mt5 import MT5Broker
from trader.config import Config
from trader.sim import run_backtest

logging.basicConfig(level=logging.WARNING)

DAYS = 366
BARS = {"M1": 420_000, "M5": 85_000, "M15": 29_000, "M30": 15_000,
        "H1": 7_500, "H4": 2_000, "D1": 400}
BASE = dict(symbol="XAUUSD", strategy="orb", pip_size=0.1,
            pip_value_per_lot=10.0, spread_pips=3.0,
            orb_session_start_hour=1, orb_box_candles=3)
RESULTS = Path("backtest-orb-1yr-results.csv")


def _fetch_chunked(cfg: Config, tf: str) -> pd.DataFrame:
    """One-shot requests above the terminal's bar limit fail with 'Invalid
    params' — pull 15-day windows via copy_rates_range and stitch them."""
    from datetime import datetime, timedelta, timezone

    mt5 = broker_mt5.mt5
    frames = []
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS)
    step = timedelta(days=15)
    t0 = start
    while t0 < end:
        t1 = min(t0 + step, end)
        rates = mt5.copy_rates_range(cfg.symbol, broker_mt5.TIMEFRAMES[tf], t0, t1)
        if rates is not None and len(rates):
            frames.append(pd.DataFrame(rates))
        t0 = t1
    if not frames:
        raise broker_mt5.MT5Error(f"no {tf} history returned in chunks")
    df = pd.concat(frames).drop_duplicates(subset="time").sort_values("time")
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df[["time", "open", "high", "low", "close"]].reset_index(drop=True)


def load_history(tf: str) -> pd.DataFrame:
    cache = Path(f"data/xauusd-{tf.lower()}-1yr.csv")
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["time"])
    cfg = Config(timeframe=tf, **BASE)
    broker_mt5.connect(cfg)
    try:
        try:
            history = MT5Broker(cfg).candles(BARS[tf])
        except broker_mt5.MT5Error:
            history = _fetch_chunked(cfg, tf)
    finally:
        broker_mt5.shutdown()
    cutoff = history["time"].max() - pd.Timedelta(days=DAYS)
    history = history[history["time"] >= cutoff].reset_index(drop=True)
    cache.parent.mkdir(exist_ok=True)
    history.to_csv(cache, index=False)
    return history


def main() -> None:
    tfs = sys.argv[1:] or ["H1"]
    rows = []
    for tf in tfs:
        history = load_history(tf)
        span = f"{history['time'].min():%Y-%m-%d} -> {history['time'].max():%Y-%m-%d}"
        print(f"\n{tf}: {len(history)} bars, {span}")
        for r in (2.0, 3.0, 4.0):
            cfg = Config(timeframe=tf, orb_tp_r=r, **BASE)
            res = run_backtest(history, cfg)
            t = res["trade_log"]
            if t.empty:
                dd = 0.0
            else:
                eq = 10_000 + t["profit"].cumsum()
                dd = float((eq - eq.cummax()).min())
            row = dict(tf=tf, tp_r=r, bars=len(history), span=span,
                       trades=res["trades"], win_rate=round(res["win_rate"], 3),
                       net_profit=round(res["net_profit"], 2), max_dd=round(dd, 2),
                       final_equity=round(res["final_equity"], 2))
            rows.append(row)
            print(f"  TP={r:.0f}R: trades={row['trades']:<4} win={row['win_rate']:.1%} "
                  f"net={row['net_profit']:+10.2f}  maxDD={row['max_dd']:+.2f}")

    df = pd.DataFrame(rows)
    header = not RESULTS.exists()
    df.to_csv(RESULTS, mode="a", header=header, index=False)
    print(f"\nappended {len(df)} rows -> {RESULTS}")


if __name__ == "__main__":
    main()
