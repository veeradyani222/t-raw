"""Structure-trailing runner vs fixed structure-target — ISOLATED analysis,
does NOT touch the live engine/sim path.

Question: this is a trend/breakout system whose edge is the runners. Instead
of exiting at a fixed structure/R target, LET THE WINNER RUN behind a
structure-trailing stop and see if pushing winners further beats the fixed
target (and beats the rejected 1R/2R/3R scale-out).

Both variants share entry, initial stop (box far side), 1%-risk sizing, the
engine's opposite-signal flip, and the 3% daily halt — so the ONLY difference
is the exit:
  - baseline : single position to the structure TP (what backtest.py does)
  - trail    : single position, NO take-profit; each bar the stop ratchets to
               the most-recent CONFIRMED fractal swing low (long) / high
               (short), never loosening. Exit on the trailing stop or a flip.

Fill model mirrors trader/sim.py: entry = close +/- spread; stop checked
against each LATER bar's low/high (stop wins ties); one position at a time;
leftover closed at the final bar.

Usage:
    python trailing_backtest.py XAUUSD H1 --from 2025-08-11 --to 2026-08-11 \
        --data data/xauusd-h1-1yr.csv
"""
import argparse

import numpy as np
import pandas as pd

from backtest import SYMBOLS, load_history
from trader.config import Config
from trader.risk import position_size_lots
from trader.strategies import orb
from trader.strategy import Setup

MIN_LOT = 0.01
# Bars of recent history scanned for the trailing swing. Bounded so the
# per-bar recompute stays cheap on M5's ~70k bars; ample to catch the most
# recent confirmed swing (fractals confirm within orb_swing_window bars).
TRAIL_SCAN = 150


def recent_swing(high: np.ndarray, low: np.ndarray, window: int, side: str):
    """Most-recent CONFIRMED fractal swing low (long) / high (short) in the
    trailing scan window, or None. Confirmation needs `window` bars on each
    side, so the last `window` bars never qualify (no lookahead)."""
    n = len(high)
    for i in range(n - window - 1, window - 1, -1):
        l, r = slice(i - window, i), slice(i + 1, i + window + 1)
        if side == "long":
            if low[i] < low[l].min() and low[i] < low[r].min():
                return float(low[i])
        else:
            if high[i] > high[l].max() and high[i] > high[r].max():
                return float(high[i])
    return None


def simulate(history: pd.DataFrame, cfg: Config, mode: str,
             equity0: float = 10_000.0) -> dict:
    h = history.reset_index(drop=True)
    n = len(h)
    time = h["time"]
    high, low, close = h["high"].values, h["low"].values, h["close"].values
    spread = cfg.spread_pips * cfg.pip_size
    lb = orb.lookback(cfg)

    equity = equity0
    curve = [equity0]
    pos = None                # the one open position, or None
    trades = []

    cur_day = None
    day_start_eq = equity
    halted = False

    def close_pos(p, price, reason):
        nonlocal equity
        pips = (price - p["entry"]) / cfg.pip_size
        if p["side"] == "short":
            pips = -pips
        profit = pips * cfg.pip_value_per_lot * p["lots"]
        equity += profit
        curve.append(equity)
        p.update(exit=price, reason=reason, profit=profit,
                 r_out=(pips * cfg.pip_size) / p["risk_dist"])
        trades.append(p)

    for i in range(n):
        # 1) stop / target fill against this bar (position opened earlier).
        #    Stop wins ties (checked first). baseline also has a fixed TP;
        #    trail has none.
        if pos is not None:
            stop_reason = "sl" if pos["tp"] is not None else "trail"
            if pos["side"] == "long":
                if low[i] <= pos["sl"]:
                    close_pos(pos, pos["sl"], stop_reason); pos = None
                elif pos["tp"] is not None and high[i] >= pos["tp"]:
                    close_pos(pos, pos["tp"], "tp"); pos = None
            else:
                if high[i] >= pos["sl"]:
                    close_pos(pos, pos["sl"], stop_reason); pos = None
                elif pos["tp"] is not None and low[i] <= pos["tp"]:
                    close_pos(pos, pos["tp"], "tp"); pos = None

        # 2) ratchet the trailing stop using structure confirmed as of bar i
        if pos is not None and mode == "trail":
            lo = max(0, i + 1 - TRAIL_SCAN)
            sw = recent_swing(high[lo:i + 1], low[lo:i + 1], cfg.orb_swing_window, pos["side"])
            if sw is not None:
                if pos["side"] == "long" and sw > pos["sl"] and sw < close[i]:
                    pos["sl"] = sw
                elif pos["side"] == "short" and sw < pos["sl"] and sw > close[i]:
                    pos["sl"] = sw

        # 3) daily anchor / halt
        d = time.iloc[i].date()
        if d != cur_day:
            cur_day, day_start_eq, halted = d, equity, False
        elif day_start_eq > 0 and (1 - equity / day_start_eq) >= cfg.daily_loss_halt:
            halted = True

        # 4) signal every bar (engine parity): opposite Setup flips, same-side
        #    can't pyramid, Blocked never closes.
        if i + 1 >= cfg.orb_box_candles + 2:
            res = orb.compute_signal(h.iloc[max(0, i + 1 - lb): i + 1], cfg)
            if isinstance(res, Setup):
                side = res.side
                if pos is not None and pos["side"] != side:
                    close_pos(pos, close[i], "signal"); pos = None
                if pos is not None or halted:
                    continue
                entry = close[i] + spread if side == "long" else close[i] - spread
                sl0 = res.sl
                risk_dist = abs(entry - sl0)
                valid = (sl0 < entry < res.tp) if side == "long" else (res.tp < entry < sl0)
                if risk_dist <= 0 or not valid:
                    continue
                sl_pips = risk_dist / cfg.pip_size
                lots = position_size_lots(equity, cfg.risk_per_trade, sl_pips,
                                          cfg.pip_value_per_lot, MIN_LOT, cfg.max_lot)
                if lots <= 0:
                    continue
                tp = res.tp if mode == "baseline" else None
                pos = dict(date=time.iloc[i], side=side, entry=entry, sl=sl0,
                           tp=tp, lots=lots, risk_dist=risk_dist)

    if pos is not None:
        close_pos(pos, close[-1], "end")

    tr = pd.DataFrame(trades)
    net = float(tr["profit"].sum()) if not tr.empty else 0.0
    wins = int((tr["profit"] > 0).sum()) if not tr.empty else 0
    n_t = len(tr)
    curve_s = pd.Series(curve)
    dd = float(((curve_s - curve_s.cummax()) / curve_s.cummax()).min()) if len(curve_s) else 0.0
    avg_r = float(tr["r_out"].mean()) if not tr.empty else 0.0
    max_r = float(tr["r_out"].max()) if not tr.empty else 0.0
    return dict(mode=mode, trades=n_t, net=net, final=equity0 + net,
                ret=net / equity0, win_rate=wins / n_t if n_t else 0.0,
                max_dd_pct=dd, avg_r=avg_r, max_r=max_r, rows=trades)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("symbol"); p.add_argument("timeframe")
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=True)
    p.add_argument("--data", default=None)
    p.add_argument("--equity", type=float, default=10_000.0)
    args = p.parse_args(argv)

    preset = SYMBOLS[args.symbol.upper()]
    cfg = Config(symbol=args.symbol.upper(), timeframe=args.timeframe.upper(),
                 strategy="orb", pip_size=preset["pip_size"],
                 pip_value_per_lot=preset["pip_value_per_lot"],
                 spread_pips=preset["spread_pips"], orb_tp_mode="structure",
                 orb_tp_r=3.0, orb_tp_min_r=1.0, orb_structure_filter=True,
                 orb_vol_filter=False, risk_per_trade=0.01,
                 daily_loss_halt=0.03, max_open_positions=1)
    start, end = pd.Timestamp(args.date_from), pd.Timestamp(args.date_to)
    history = load_history(cfg, start, end, args.data, need_volume=False)
    history = history[(history["time"] >= start) & (history["time"] < end + pd.Timedelta(days=1))]

    base = simulate(history, cfg, "baseline", args.equity)
    trail = simulate(history, cfg, "trail", args.equity)

    span = f"{history['time'].min():%Y-%m-%d} -> {history['time'].max():%Y-%m-%d}"
    print(f"\n=== {cfg.symbol} {cfg.timeframe}  {span}  ({len(history)} bars, ${args.equity:,.0f} @1% risk) ===")
    print(f"{'':10}{'trades':>8}{'net P/L':>11}{'return':>9}{'win%':>7}{'maxDD%':>8}{'avgR':>7}{'maxR':>8}")
    for r in (base, trail):
        print(f"{r['mode']:10}{r['trades']:>8}{r['net']:>+11.2f}{r['ret']:>+9.1%}"
              f"{r['win_rate']:>7.0%}{r['max_dd_pct']:>8.1%}{r['avg_r']:>+7.2f}{r['max_r']:>+8.2f}")
    return base, trail


if __name__ == "__main__":
    main()
