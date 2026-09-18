"""Offline bid-OHLC simulator; timestamps and loss-reset days use the dataset clock.

Signals refer to completed bars and execute at the following open. OHLC cannot
resolve tick order: adverse excursion is visited first and stop wins a tie. Spread
is constant within a bar. Missing 20:00 bars can cause unavoidable gap exposure;
the next available open settles it and attributes that P/L to the preceding day.
Internal guards block new entries; they never manufacture threshold-price exits.
"""
from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SimConfig:
    start_equity: float = 10000.
    loss_baseline: float = 10000.
    risk: float = .0025
    daily_limit: float = .03
    total_limit: float = .06
    firm_daily_limit: float = .04
    firm_total_limit: float = .08
    spread_floor: float = .30
    commission_per_lot: float = 7.
    slippage: float = .03
    point: float = .01
    contract_size: float = 100.
    min_lot: float = .01
    max_lot: float = 1.
    lot_step: float = .01
    max_observed_spread: float = .60
    entry_start_hour: int = 7
    entry_end_hour: int = 19
    flat_hour: int = 20


TRADE_COLUMNS = ["entry_time", "exit_time", "side", "entry", "exit", "sl", "tp",
                 "lots", "gross_profit", "commission", "profit", "equity_after", "reason"]
DAILY_COLUMNS = ["date", "start_equity", "end_equity", "net_profit", "min_equity",
                 "worst_loss", "internal_halt", "firm_breach"]


def simulate(df, signals, *, start, end=None, config=None):
    """Return summary, closed trades and daily accounting for [start, end).

    ``signals`` must have matching row order, side (-1/0/1), absolute executable
    stop/target prices, and max_hold (completed bars after entry). Risk is a
    fraction of current cash equity, bounded by daily/static-total headroom.
    Percent outputs use percentage points (e.g. 3.0 means 3%).
    """
    cfg = config or SimConfig()
    if len(df) != len(signals):
        raise ValueError("signals must have the same length as bars")
    if (cfg.start_equity <= 0 or cfg.loss_baseline <= 0 or cfg.risk <= 0
            or cfg.contract_size <= 0 or cfg.lot_step <= 0 or cfg.min_lot <= 0
            or cfg.max_lot < cfg.min_lot or not 0 < cfg.daily_limit <= cfg.firm_daily_limit < 1
            or not 0 < cfg.total_limit <= cfg.firm_total_limit < 1
            or min(cfg.spread_floor, cfg.commission_per_lot, cfg.slippage, cfg.point) < 0):
        raise ValueError("invalid risk, cost or contract configuration")
    times = pd.DatetimeIndex(pd.to_datetime(df["time"] if "time" in df else df.index))
    if times.hasnans or not times.is_monotonic_increasing or times.has_duplicates:
        raise ValueError("bar timestamps must be unique and increasing")
    if isinstance(signals.index, pd.DatetimeIndex) and not signals.index.equals(times):
        raise ValueError("signal timestamps must match bars")
    values = df[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("OHLC prices must be finite")
    if len(values) and np.any((values[:, 1] < np.maximum(values[:, 0], values[:, 3]))
                             | (values[:, 2] > np.minimum(values[:, 0], values[:, 3]))):
        raise ValueError("invalid OHLC ranges")
    observed = (df["spread"].to_numpy(dtype=float) * cfg.point
                if "spread" in df else np.zeros(len(df)))
    if np.any(~np.isfinite(observed)) or np.any(observed < 0):
        raise ValueError("spread must be finite nonnegative points")
    spreads = np.maximum(observed, cfg.spread_floor)
    sig = signals[["side", "sl", "tp", "max_hold"]].to_numpy(dtype=float)
    begin = times.searchsorted(pd.Timestamp(start), side="left")
    finish = len(df) if end is None else times.searchsorted(pd.Timestamp(end), side="left")
    # Precompute Python scalars: repeatedly indexing a DatetimeIndex dominates
    # runtime in long, mostly-flat screening runs.
    timestamps = list(times)
    hours = times.hour.to_list()
    days = times.normalize().asi8.tolist()
    balance = cfg.start_equity
    peak = minimum = balance
    max_dd = worst_day = 0.
    total_halt = None
    daily_halts, firm_days = [], []
    firm_total_time = None
    trades, daily = [], []
    position = None
    day = None
    day_key = None
    day_anchor = day_min = balance
    day_halt = day_firm = False
    static_floor = cfg.loss_baseline * (1 - cfg.total_limit)
    firm_floor = cfg.loss_baseline * (1 - cfg.firm_total_limit)

    def mark(equity, timestamp):
        nonlocal peak, minimum, max_dd, worst_day, day_min
        nonlocal day_halt, day_firm, total_halt, firm_total_time
        peak = max(peak, equity)
        minimum = min(minimum, equity)
        max_dd = max(max_dd, peak - equity)
        day_min = min(day_min, equity)
        loss = max(0., day_anchor - equity)
        worst_day = max(worst_day, loss)
        if not day_halt and loss >= cfg.loss_baseline * cfg.daily_limit - 1e-8:
            day_halt = True
            daily_halts.append(day)
        if total_halt is None and equity <= static_floor + 1e-8:
            total_halt = timestamp
        if not day_firm and loss >= cfg.loss_baseline * cfg.firm_daily_limit - 1e-8:
            day_firm = True
            firm_days.append(day)
        if firm_total_time is None and equity <= firm_floor + 1e-8:
            firm_total_time = timestamp

    def liquidation(price):
        p = position
        return balance + p["side"] * (price - p["entry"]) * p["lots"] * cfg.contract_size - p["fee"]

    def close_position(price, timestamp, reason):
        nonlocal balance, position
        p = position
        gross = p["side"] * (price - p["entry"]) * p["lots"] * cfg.contract_size
        balance += gross - p["fee"]
        mark(balance, timestamp)
        trades.append({"entry_time": p["time"], "exit_time": timestamp, "side": p["side"],
                       "entry": p["entry"], "exit": price, "sl": p["sl"], "tp": p["tp"],
                       "lots": p["lots"], "gross_profit": gross, "commission": 2 * p["fee"],
                       "profit": gross - 2 * p["fee"], "equity_after": balance, "reason": reason})
        position = None

    def end_day():
        daily.append({"date": day, "start_equity": day_anchor, "end_equity": balance,
                      "net_profit": balance - day_anchor, "min_equity": day_min,
                      "worst_loss": max(0., day_anchor - day_min),
                      "internal_halt": day_halt, "firm_breach": day_firm})

    for i in range(begin, finish):
        timestamp = timestamps[i]
        op, hi, lo, cl = values[i]
        spread = spreads[i]
        if days[i] != day_key:
            if day is not None:
                if position is not None:
                    p = position
                    executable = op if p["side"] == 1 else op + spread
                    # Resting orders remain active across missing bars.
                    if p["side"] * (executable - p["sl"]) <= 0:
                        close_position(executable - p["side"] * cfg.slippage, timestamp, "sl")
                    elif p["side"] * (executable - p["tp"]) >= 0:
                        close_position(p["tp"], timestamp, "tp")
                    else:
                        close_position(executable - p["side"] * cfg.slippage, timestamp, "day_gap")
                end_day()
            day = timestamp.normalize()
            day_key = days[i]
            day_anchor = day_min = balance
            day_halt = day_firm = False
            mark(balance, timestamp)
        # No inherited pre-window or preceding-day signals.
        side, sl, tp, hold = sig[i - 1] if i > begin and days[i - 1] == day_key else (0, 0, 0, 0)
        if position is not None:
            p = position
            executable = op if p["side"] == 1 else op + spread
            if p["side"] * (executable - p["sl"]) <= 0:
                close_position(executable - p["side"] * cfg.slippage, timestamp, "sl")
            elif p["side"] * (executable - p["tp"]) >= 0:
                close_position(p["tp"], timestamp, "tp")
            else:
                mark(liquidation(executable - p["side"] * cfg.slippage), timestamp)
                reason = ("flat_hour" if hours[i] >= cfg.flat_hour else
                          "opposite" if side == -p["side"] else
                          "max_hold" if i - p["bar"] >= p["hold"] else None)
                if reason:
                    close_position(executable - p["side"] * cfg.slippage, timestamp, reason)
        if (position is None and not day_halt and total_halt is None
                and cfg.entry_start_hour <= hours[i] < min(cfg.entry_end_hour, cfg.flat_hour)
                and side in (-1, 1) and observed[i] <= cfg.max_observed_spread
                and np.isfinite([sl, tp, hold]).all() and hold >= 1):
            entry = op + spread + cfg.slippage if side == 1 else op - cfg.slippage
            executable = op if side == 1 else op + spread
            # Gap-invalidated orders are skipped instead of granting impossible entries.
            if side * (executable - sl) > 0 and side * (tp - entry) > 0:
                per_lot = (side * (entry - sl) + cfg.slippage) * cfg.contract_size + cfg.commission_per_lot
                budget = min(balance * cfg.risk,
                             balance - (day_anchor - cfg.loss_baseline * cfg.daily_limit),
                             balance - static_floor)
                lots = math.floor((min(cfg.max_lot, budget / per_lot) + 1e-12) / cfg.lot_step) * cfg.lot_step
                lots = round(lots, 10)
                if lots >= cfg.min_lot:
                    fee = lots * cfg.commission_per_lot / 2
                    position = {"side": int(side), "entry": entry, "sl": sl, "tp": tp,
                                "hold": int(hold), "lots": lots, "fee": fee, "bar": i, "time": timestamp}
                    balance -= fee
                    mark(liquidation(executable - side * cfg.slippage), timestamp)
        if position is not None:
            p = position
            adverse = lo if p["side"] == 1 else hi + spread
            favorable = hi if p["side"] == 1 else lo + spread
            if p["side"] * (adverse - p["sl"]) <= 0:
                close_position(p["sl"] - p["side"] * cfg.slippage, timestamp, "sl")
            else:
                mark(liquidation(adverse - p["side"] * cfg.slippage), timestamp)
                if p["side"] * (favorable - p["tp"]) >= 0:
                    close_position(p["tp"], timestamp, "tp")
                else:
                    mark(liquidation(favorable - p["side"] * cfg.slippage), timestamp)
                    executable = cl if p["side"] == 1 else cl + spread
                    mark(liquidation(executable - p["side"] * cfg.slippage), timestamp)
    if position is not None:
        side = position["side"]
        executable = values[finish - 1, 3] + (spreads[finish - 1] if side == -1 else 0)
        close_position(executable - side * cfg.slippage, times[finish - 1], "end")
    if day is not None:
        end_day()
    trade_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    profits = trade_df["profit"].to_numpy(dtype=float)
    wins = int(np.sum(profits > 0))
    gains, losses = profits[profits > 0].sum(), -profits[profits < 0].sum()
    summary = {"net_profit": balance - cfg.start_equity, "final_equity": balance,
               "trades_count": len(trades), "wins": wins,
               "win_rate": 100 * wins / len(trades) if trades else 0.,
               "profit_factor": gains / losses if losses > 0 else (float("inf") if gains > 0 else 0.),
               "peak_equity": peak, "min_equity": minimum, "max_float_dd": max_dd,
               "max_float_dd_pct": 100 * max_dd / cfg.loss_baseline,
               "worst_day_loss": worst_day, "worst_day_loss_pct": 100 * worst_day / cfg.loss_baseline,
               "internal_total_halt": total_halt, "internal_daily_halts": len(daily_halts),
               "internal_daily_halt_dates": daily_halts,
               "firm_breach": bool(firm_days or firm_total_time is not None),
               "firm_daily_breach": bool(firm_days), "firm_daily_breaches": len(firm_days),
               "firm_daily_breach_dates": firm_days,
               "firm_total_breach": firm_total_time is not None,
               "firm_total_breaches": int(firm_total_time is not None),
               "firm_total_breach_time": firm_total_time,
               "first_trade": trades[0]["entry_time"] if trades else None,
               "last_trade": trades[-1]["exit_time"] if trades else None}
    return {"summary": summary, "trades": trade_df, "daily": pd.DataFrame(daily, columns=DAILY_COLUMNS)}
