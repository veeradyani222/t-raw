"""Scale-out (partial-exit) what-if backtest — ISOLATED analysis, does NOT
touch the live engine/sim path.

Question being answered: instead of one position per ORB signal exiting at a
single structure/R target, split the SAME 1%-risk position into legs that
take profit at 1R / 2R / 3R (all sharing the box-far-side stop). Whether the
3rd leg exists is decided by the structure target's reach:

    R_target >= 3     -> 3 legs at 1R / 2R / 3R  (1/3 position each)
    2 <= R_target < 3 -> 2 legs, both at 2R      (1/2 position each)
    R_target < 2      -> 1 leg at the structure target (edge case, counted)

R_target = distance to the structure-derived TP, in multiples of the stop
distance. When compute_signal falls back to its R-multiple target (no swing
level), that fallback is orb_tp_r (=3), so it takes 3 legs.

Fill model mirrors trader/sim.py exactly: entry = signal bar close +/- spread;
SL/TP checked against each LATER bar's high/low; SL wins ties (pessimistic);
only one signal live at a time (max_open_positions = 1); leftover legs closed
at the final bar. Sizing compounds off realized equity, like the engine.

Two variants are simulated on the same harness so the diff is apples-to-apples:
  - baseline : one full-size leg to the structure TP (what backtest.py does)
  - scaleout : the multi-leg rule above

Usage:
    python scaleout_backtest.py XAUUSD H1 --from 2026-07-11 --to 2026-08-11 \
        --data data/xauusd-h1-1yr.csv
"""
import argparse
from dataclasses import replace

import pandas as pd

from backtest import SYMBOLS, load_history
from trader.config import Config
from trader.risk import position_size_lots
from trader.strategies import orb
from trader.strategy import Setup

MIN_LOT = 0.01


def leg_plan(kind: str, r_target: float) -> list[tuple[float, float]]:
    """Return [(target_R, position_fraction), ...] for a signal.

    baseline -> single leg at the structure target (fraction 1.0, R carried
    separately by the caller). scaleout -> the 1R/2R/3R rule.
    """
    if kind == "baseline":
        return [(r_target, 1.0)]
    if r_target >= 3:
        return [(1.0, 1 / 3), (2.0, 1 / 3), (3.0, 1 / 3)]
    if r_target >= 2:
        return [(2.0, 1 / 2), (2.0, 1 / 2)]
    return [(r_target, 1.0)]


def simulate(history: pd.DataFrame, cfg: Config, kind: str,
             equity0: float = 10_000.0) -> dict:
    h = history.reset_index(drop=True)
    n = len(h)
    time = h["time"]
    high, low, close = h["high"].values, h["low"].values, h["close"].values
    spread = cfg.spread_pips * cfg.pip_size
    lb = orb.lookback(cfg)

    equity = equity0                     # realized only, like sim.py
    curve = [equity0]                    # realized-equity samples for drawdown
    open_legs: list[dict] = []           # legs from the one live signal
    signals: list[dict] = []             # one row per entry (aggregated legs)
    active: dict | None = None           # the signal currently holding legs

    # daily-loss halt, matching the engine default (3%)
    cur_day = None
    day_start_eq = equity
    halted = False

    def settle(leg: dict, price: float, reason: str):
        nonlocal equity
        pips = (price - leg["entry"]) / cfg.pip_size
        if leg["side"] == "short":
            pips = -pips
        profit = pips * cfg.pip_value_per_lot * leg["lots"]
        equity += profit
        curve.append(equity)
        leg["exit"] = price
        leg["profit"] = profit
        leg["reason"] = reason

    for i in range(n):
        # 1) fill stops/targets against this bar (legs opened on a PRIOR bar)
        for leg in list(open_legs):
            hit = None
            if leg["side"] == "long":
                if low[i] <= leg["sl"]:
                    hit = (leg["sl"], "sl")
                elif high[i] >= leg["tp"]:
                    hit = (leg["tp"], "tp")
            else:
                if high[i] >= leg["sl"]:
                    hit = (leg["sl"], "sl")
                elif low[i] <= leg["tp"]:
                    hit = (leg["tp"], "tp")
            if hit:
                settle(leg, *hit)
                open_legs.remove(leg)

        # 2) daily anchor / halt (realized equity)
        d = time.iloc[i].date()
        if d != cur_day:
            cur_day, day_start_eq, halted = d, equity, False
        elif day_start_eq > 0 and (1 - equity / day_start_eq) >= cfg.daily_loss_halt:
            halted = True

        # a signal is done once all its legs have closed via stops
        if active is not None and not open_legs:
            active = None

        # 3) evaluate the signal EVERY bar, like the engine's on_bar. A valid
        #    OPPOSITE setup closes the current position at market and flips
        #    (engine.py's crossover close) — this happens even if the new entry
        #    is then blocked by the halt. Same-side setups can't pyramid
        #    (max_open_positions = 1). Blocked setups never close a position.
        if i + 1 >= cfg.orb_box_candles + 2:
            window = h.iloc[max(0, i + 1 - lb): i + 1]
            res = orb.compute_signal(window, cfg)
            if isinstance(res, Setup):
                side = res.side
                # opposite-signal close at this bar's close
                if active is not None and active["side"] != side:
                    for leg in list(open_legs):
                        settle(leg, close[i], "signal")
                        open_legs.remove(leg)
                    active = None
                # same-side position already open -> slot full, skip
                if active is not None:
                    continue
                if halted:
                    continue
                entry = close[i] + spread if side == "long" else close[i] - spread
                sl = res.sl
                risk_dist = abs(entry - sl)
                valid = (sl < entry < res.tp) if side == "long" else (res.tp < entry < sl)
                if risk_dist > 0 and valid:
                    sl_pips = risk_dist / cfg.pip_size
                    # structure reach in R, measured off the ACTUAL entry/stop
                    if res.meta.get("tp_source") == "structure":
                        r_target = abs(res.tp - entry) / risk_dist
                    else:
                        r_target = cfg.orb_tp_r
                    plan = leg_plan(kind, r_target)

                    if kind == "baseline":
                        full = position_size_lots(equity, cfg.risk_per_trade,
                                                  sl_pips, cfg.pip_value_per_lot,
                                                  MIN_LOT, cfg.max_lot)
                        if full <= 0:
                            continue
                        full_raw = full
                    else:
                        full_raw = (equity * cfg.risk_per_trade) / (sl_pips * cfg.pip_value_per_lot)
                        if full_raw < MIN_LOT:      # engine would skip this trade
                            continue

                    legs = []
                    for r_mult, frac in plan:
                        lots = round(frac * full_raw + 1e-9, 2)
                        if lots < MIN_LOT:
                            lots = MIN_LOT          # min-lot floor (inflates risk)
                        tp = entry + r_mult * risk_dist if side == "long" \
                            else entry - r_mult * risk_dist
                        leg = dict(side=side, entry=entry, sl=sl, tp=tp,
                                   lots=lots, r_mult=r_mult)
                        legs.append(leg)
                        open_legs.append(leg)

                    total_lots = sum(l["lots"] for l in legs)
                    active = dict(
                        date=time.iloc[i], side=side, entry=entry, sl=sl,
                        risk_dist=risk_dist, r_target=r_target, legs=legs,
                        n_legs=len(legs), total_lots=total_lots,
                        eff_risk=total_lots * sl_pips * cfg.pip_value_per_lot / equity,
                    )
                    signals.append(active)

    # close whatever is still open at the last bar
    for leg in list(open_legs):
        settle(leg, close[-1], "end")

    # ---- aggregate ------------------------------------------------------
    for s in signals:
        s["profit"] = sum(l["profit"] for l in s["legs"])
    net = sum(s["profit"] for s in signals)
    wins = sum(1 for s in signals if s["profit"] > 0)
    n_sig = len(signals)
    all_legs = [l for s in signals for l in s["legs"]]
    leg_tp = sum(1 for l in all_legs if l["reason"] == "tp")
    leg_sl = sum(1 for l in all_legs if l["reason"] == "sl")
    leg_end = sum(1 for l in all_legs if l["reason"] == "end")
    curve_s = pd.Series(curve)
    max_dd = float((curve_s - curve_s.cummax()).min())
    max_dd_pct = float(((curve_s - curve_s.cummax()) / curve_s.cummax()).min())
    return dict(
        kind=kind, signals=n_sig, net=net, final=equity0 + net,
        ret=net / equity0, win_rate=wins / n_sig if n_sig else 0.0,
        max_dd=max_dd, max_dd_pct=max_dd_pct,
        wins=wins, n3=sum(1 for s in signals if s["n_legs"] == 3),
        n2=sum(1 for s in signals if s["n_legs"] == 2),
        n1=sum(1 for s in signals if s["n_legs"] == 1),
        eff_risk=sum(s["eff_risk"] for s in signals) / n_sig if n_sig else 0.0,
        legs=len(all_legs), leg_tp=leg_tp, leg_sl=leg_sl, leg_end=leg_end,
        signal_rows=signals,
    )


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("symbol")
    p.add_argument("timeframe")
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=True)
    p.add_argument("--data", default=None)
    p.add_argument("--equity", type=float, default=10_000.0)
    args = p.parse_args(argv)

    preset = SYMBOLS[args.symbol.upper()]
    cfg = Config(
        symbol=args.symbol.upper(), timeframe=args.timeframe.upper(),
        strategy="orb", pip_size=preset["pip_size"],
        pip_value_per_lot=preset["pip_value_per_lot"],
        spread_pips=preset["spread_pips"],
        orb_tp_mode="structure", orb_tp_r=3.0, orb_tp_min_r=1.0,
        orb_structure_filter=True, orb_vol_filter=False,
        risk_per_trade=0.01, daily_loss_halt=0.03, max_open_positions=1,
    )
    start, end = pd.Timestamp(args.date_from), pd.Timestamp(args.date_to)
    history = load_history(cfg, start, end, args.data, need_volume=False)
    history = history[(history["time"] >= start) & (history["time"] < end + pd.Timedelta(days=1))]

    base = simulate(history, cfg, "baseline", args.equity)
    scal = simulate(history, cfg, "scaleout", args.equity)

    span = f"{history['time'].min():%Y-%m-%d} -> {history['time'].max():%Y-%m-%d}"
    print(f"\n=== {cfg.symbol} {cfg.timeframe}  {span}  ({len(history)} bars, ${args.equity:,.0f} @1% risk) ===")
    hdr = f"{'':14}{'signals':>9}{'net P/L':>11}{'return':>9}{'win%':>7}{'maxDD%':>8}{'end equity':>12}"
    print(hdr)
    for r in (base, scal):
        print(f"{r['kind']:14}{r['signals']:>9}{r['net']:>+11.2f}{r['ret']:>+9.1%}"
              f"{r['win_rate']:>7.0%}{r['max_dd_pct']:>8.1%}{r['final']:>12.2f}")
    print(f"  scaleout legs: {scal['n3']}×3-leg, {scal['n2']}×2-leg, {scal['n1']}×1-leg"
          f"  | leg exits: {scal['leg_tp']} TP / {scal['leg_sl']} SL / {scal['leg_end']} open-at-end"
          f"  | avg effective risk {scal['eff_risk']:.2%}")
    return base, scal


if __name__ == "__main__":
    main()
