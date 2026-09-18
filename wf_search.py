"""Simulation and walk-forward utilities for BOS research.

Signal builders live in bos_backtest.py. This module contains no trading
strategy. Use allow_flip=True when comparing research to the live engine.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from trader.risk import position_size_lots
import backtest as bt

SYM = os.environ.get("WF_SYM", "XAUUSD").upper()
PRESET = bt.SYMBOLS[SYM]
PIP = PRESET["pip_size"]
PIP_VALUE = PRESET["pip_value_per_lot"]
SPREAD = PRESET["spread_pips"]
RISK = 0.01
START_EQUITY = 10_000.0
MIN_LOT, MAX_LOT = 0.01, 1.0


@dataclass
class Entry:
    """What a strategy asks the harness to open on this bar."""
    side: str                     # "long" | "short"
    sl: float                     # stop PRICE (required — used for sizing)
    tp: float | None = None       # target PRICE, or None to exit only by time/stop
    max_hold: int | None = None   # close at entry_bar + max_hold (bars), or None
    exit_hour: int | None = None  # close at the first later bar whose hour == this
    meta: dict = field(default_factory=dict)


def simulate(df: pd.DataFrame, signal_fn, *, allow_flip=False,
             spread=SPREAD, pip=PIP, pip_value=PIP_VALUE, risk=RISK,
             start_equity=START_EQUITY, daily_halt=0.0, loss_baseline=0.0,
             total_halt=0.0, max_dd=0.0) -> dict:
    """Mirror of trader.sim: cursor advances bar by bar; stops on the new bar
    are filled BEFORE a fresh signal is computed at that bar's close.

    signal_fn(df, i) -> Entry | None, where i is the latest CLOSED bar. It sees
    df.iloc[:i+1] only (the harness passes the whole frame; strategies must not
    peek past i).

    Prop rails (all default 0 = off, preserving the validated behavior): when
    set, the SAME trader.risk.RiskGuard the live bot uses gates entries — daily
    loss halt, and permanent total-loss / max-drawdown halt.
    """
    from trader.risk import RiskGuard
    # RiskGuard treats daily_loss_halt=0.0 as a 0% threshold (halts immediately),
    # not "off" — so only engage the guard when a rail is actually set.
    rails_on = daily_halt > 0 or loss_baseline > 0 or total_halt > 0 or max_dd > 0
    guard = RiskGuard(1, daily_halt, max_dd, loss_baseline, total_halt)
    blown_at = None
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    openp = df["open"].values
    times = df["time"].values
    hours = pd.DatetimeIndex(df["time"]).hour.values
    n = len(df)

    equity = start_equity
    pos = None  # dict: side, entry, sl, tp, lots, risk_amt, entry_bar, exit_hour, max_hold, meta
    trades = []
    spread_p = spread * pip

    def settle(price, reason, exit_bar):
        nonlocal equity, pos
        pips = (price - pos["entry"]) / pip
        if pos["side"] == "short":
            pips = -pips
        profit = pips * pip_value * pos["lots"]
        equity += profit
        trades.append({
            "entry_time": times[pos["entry_bar"]], "exit_time": times[exit_bar],
            "side": pos["side"], "entry": pos["entry"], "exit": price,
            "sl": pos["sl"], "tp": pos["tp"], "lots": pos["lots"],
            "profit": profit, "reason": reason,
            "bars_held": exit_bar - pos["entry_bar"],
            "r_multiple": profit / pos["risk_amt"] if pos["risk_amt"] > 0 else np.nan,
            "equity_after": equity, **pos["meta"],
        })
        pos = None

    for i in range(n):
        # 1) fill stops/targets/time-exit against THIS bar (position opened <= i-1)
        if pos is not None:
            hit = False
            if pos["side"] == "long":
                if low[i] <= pos["sl"]:
                    settle(pos["sl"], "sl", i); hit = True
                elif pos["tp"] is not None and high[i] >= pos["tp"]:
                    settle(pos["tp"], "tp", i); hit = True
            else:
                if high[i] >= pos["sl"]:
                    settle(pos["sl"], "sl", i); hit = True
                elif pos["tp"] is not None and low[i] <= pos["tp"]:
                    settle(pos["tp"], "tp", i); hit = True
            if not hit and pos is not None:
                time_up = (pos["max_hold"] is not None
                           and i - pos["entry_bar"] >= pos["max_hold"])
                hour_up = (pos["exit_hour"] is not None and hours[i] == pos["exit_hour"])
                if time_up or hour_up:
                    settle(close[i], "time", i)

        # prop rails: refresh the daily/total halt state with current equity
        if rails_on:
            guard.on_new_bar(pd.Timestamp(times[i]).date(), equity)
            if guard.blown and blown_at is None:
                blown_at = pd.Timestamp(times[i])

        # 2) compute a fresh signal at this bar's close
        sig = signal_fn(df, i)
        if sig is None:
            continue

        # 3) opposite-signal flip closes the open position first (engine parity)
        if pos is not None and allow_flip and sig.side != pos["side"]:
            settle(close[i], "signal", i)

        if pos is not None:  # max 1 position
            continue

        # prop rails: daily/total halt blocks new entries (never force-closes)
        if rails_on and not guard.may_open(0)[0]:
            continue

        price = close[i]
        entry = price + spread_p if sig.side == "long" else price - spread_p
        # engine's levels-valid check
        if sig.side == "long":
            valid = sig.sl < price and (sig.tp is None or price < sig.tp)
        else:
            valid = sig.sl > price and (sig.tp is None or price > sig.tp)
        if not valid:
            continue
        # Engine parity: size from the raw close->SL distance (engine.py sizes
        # off `price`, the close), but measure realized risk from the actual
        # spread-adjusted entry (sim.open_position does).
        sl_pips = abs(price - sig.sl) / pip
        lots = position_size_lots(equity, risk, sl_pips, pip_value, MIN_LOT, MAX_LOT)
        if lots <= 0:
            continue
        pos = {"side": sig.side, "entry": entry, "sl": sig.sl, "tp": sig.tp,
               "lots": lots, "risk_amt": abs(entry - sig.sl) / pip * pip_value * lots,
               "entry_bar": i, "exit_hour": sig.exit_hour, "max_hold": sig.max_hold,
               "meta": sig.meta}

    if pos is not None:
        settle(close[-1], "end", n - 1)

    t = pd.DataFrame(trades)
    if t.empty:
        return dict(trades=0, wins=0, win_rate=0.0, net=0.0, max_dd=0.0,
                    final_equity=start_equity, trade_log=t, blown_at=blown_at)
    eq = start_equity + t["profit"].cumsum()
    return dict(
        trades=len(t), wins=int((t["profit"] > 0).sum()),
        win_rate=float((t["profit"] > 0).mean()),
        net=float(t["profit"].sum()),
        max_dd=float((eq - eq.cummax()).min()),
        final_equity=float(eq.iloc[-1]), trade_log=t, blown_at=blown_at)


def folds(df, train_years=2, test_months=6, step_months=6):
    out = []
    t0 = df["time"].min().normalize()
    end = df["time"].max()
    tr_start = t0
    while True:
        tr_end = tr_start + pd.DateOffset(years=train_years)
        te_end = tr_end + pd.DateOffset(months=test_months)
        if te_end > end + pd.Timedelta(days=1):
            break
        train = df[(df["time"] >= tr_start) & (df["time"] < tr_end)]
        test = df[(df["time"] >= tr_end) & (df["time"] < te_end)]
        out.append((train.reset_index(drop=True), test.reset_index(drop=True),
                    f"{tr_end:%Y-%m}..{te_end:%Y-%m}"))
        tr_start = tr_start + pd.DateOffset(months=step_months)
    return out


def walk_forward(name, df, search_fn, build_fn, **fold_kw):
    fs = folds(df, **fold_kw)
    print(f"\n=== WALK-FORWARD: {name} === ({len(fs)} OOS test folds, "
          f"train={fold_kw.get('train_years', 2)}yr / "
          f"test={fold_kw.get('test_months', 6)}mo)")
    print(f"{'test window':<18}{'trades':>7}{'win%':>7}{'net$':>10}{'maxDD$':>10}  params")
    rows = []
    for train, test, label in fs:
        p = search_fn(train)
        if p is None:
            print(f"{label:<18}{'-- no params cleared min-trades on train --':>34}")
            continue
        r = simulate(test, build_fn(test, **p))
        rows.append(r)
        pstr = ",".join(f"{k}={v}" for k, v in p.items())
        print(f"{label:<18}{r['trades']:>7}{r['win_rate']*100:>6.1f}%"
              f"{r['net']:>+10.0f}{r['max_dd']:>+10.0f}  {pstr}")
    if rows:
        net = sum(r["net"] for r in rows)
        tot = sum(r["trades"] for r in rows)
        pos = sum(1 for r in rows if r["net"] > 0)
        big = [r for r in rows if r["trades"] >= 20]
        pos_big = sum(1 for r in big if r["net"] > 0)
        print(f"{'-'*60}")
        print(f"AGGREGATE OOS: net={net:+.0f}  trades={tot}  "
              f"folds positive={pos}/{len(rows)}  "
              f"(folds >=20 trades: {pos_big}/{len(big)} positive)")
    return rows


def per_year(name, df, build_fn):
    """Evaluate ONE fixed (a-priori) config over the whole history, no training.
    Nothing is fit, so the entire span is a fair test."""
    r = simulate(df, build_fn(df))
    t = r["trade_log"]
    print(f"\n=== FIXED CONFIG (no per-fold tuning): {name} ===")
    print(f"{'year':<6}{'trades':>7}{'win%':>7}{'net$':>10}")
    if not t.empty:
        t = t.copy()
        t["year"] = pd.DatetimeIndex(t["entry_time"]).year
        for y, g in t.groupby("year"):
            print(f"{y:<6}{len(g):>7}{(g['profit']>0).mean()*100:>6.1f}%{g['profit'].sum():>+10.0f}")
    yrs = t["entry_time"].dt.year.nunique() if not t.empty else 0
    pos_years = 0
    if not t.empty:
        by = t.groupby(pd.DatetimeIndex(t["entry_time"]).year)["profit"].sum()
        pos_years = int((by > 0).sum())
    print(f"{'-'*30}")
    print(f"TOTAL net={r['net']:+.0f}  trades={r['trades']}  win={r['win_rate']*100:.1f}%  "
          f"maxDD={r['max_dd']:+.0f}  positive years={pos_years}/{yrs}")
    return r
