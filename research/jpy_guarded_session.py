"""Offline cross-JPY replay with liquidation-equity drawdown guards."""

import math

import numpy as np
import pandas as pd

from research.jpy_session_recheck import signal_inputs


TRADE_COLUMNS = ["entry_time", "exit_time", "entry", "exit", "sl", "lots",
                 "gross", "fees", "profit", "equity_after", "reason", "fx_used",
                 "planned_risk", "entry_balance", "entry_daily_headroom",
                 "entry_static_headroom"]


def simulate(df, start, end, *, initial_balance=10000., spread_pips=2.5,
             commission=14., slip_pips=.1, entry_at_open=False):
    """Replay hour-0 longs, at the close by default or the open when requested.

    Bars carry dataset timestamps (no timezone inference). Intrabar fills and
    liquidation marks use previous USDJPY close; completed-close marks and time
    exits use contemporaneous USDJPY close. Only one position can be open.
    Internal limits are 3% daily / 6% static; diagnostic firm limits are 4% / 8%.
    A threshold touch activates the guard; a breach requires a strict crossing.
    """
    if not math.isfinite(initial_balance) or initial_balance <= 0:
        raise ValueError("initial_balance must be positive and finite")
    if any(not math.isfinite(v) or v < 0 for v in (spread_pips, commission, slip_pips)):
        raise ValueError("Costs must be nonnegative and finite")
    times = pd.DatetimeIndex(df.time)
    if not times.is_monotonic_increasing or times.has_duplicates:
        raise ValueError("Bars must have sorted, unique timestamps")
    values = df[["open", "high", "low", "close", "fx", "fx_previous"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, 4:] <= 0).any():
        raise ValueError("Prices and FX must be finite; FX must be positive")
    side, stops = signal_inputs(df, 0)
    if entry_at_open:
        # ATR/stop from completed history, including across weekends.
        _, old_stops = signal_inputs(df, 23)
        stops = np.r_[np.nan, old_stops[:-1]]
        side = (times.hour == 0) & np.isfinite(stops) & (stops < df.close.shift().to_numpy())
        side[:15] = False
    indices = np.flatnonzero((times >= start) & (times < end))
    spread, slip = spread_pips*.01, slip_pips*.01
    static_floor = initial_balance*.94
    daily_allowance = initial_balance*.03
    epsilon = initial_balance*1e-10
    balance = float(initial_balance)
    pos, day, permanent_halt, first_static_block = None, None, None, None
    day_anchor = balance
    min_equity, max_daily_loss = balance, 0.
    trades, daily_guard_days, internal_daily_days, firm_daily_days = [], set(), set(), set()
    internal_static_breach = firm_static_breach = False
    blocked = dict(blocked_entries=0, blocked_daily=0, blocked_static=0,
                   blocked_concurrent=0, blocked_min_lot=0)

    def observe(equity, i):
        nonlocal min_equity, max_daily_loss, permanent_halt
        nonlocal internal_static_breach, firm_static_breach
        min_equity = min(min_equity, equity)
        max_daily_loss = max(max_daily_loss, day_anchor-equity)
        if equity <= day_anchor-daily_allowance+epsilon:
            daily_guard_days.add(day)
        if equity <= static_floor+epsilon and permanent_halt is None:
            permanent_halt = times[i]
        if equity < day_anchor-daily_allowance-epsilon:
            internal_daily_days.add(day)
        if equity < static_floor-epsilon:
            internal_static_breach = True
        if equity < day_anchor-initial_balance*.04-epsilon:
            firm_daily_days.add(day)
        if equity < initial_balance*.92-epsilon:
            firm_static_breach = True

    def liquidation_equity(bid, rate):
        return balance+(bid-slip-pos["entry"])*100000*pos["lots"]/rate-pos["lots"]*commission/2

    def settle(price, rate, i, reason):
        nonlocal balance, pos
        gross = (price-pos["entry"])*100000*pos["lots"]/rate
        fees = pos["lots"]*commission
        balance += gross-fees/2
        trades.append(dict(entry_time=times[pos["bar"]], exit_time=times[i],
                           entry=pos["entry"], exit=price, sl=pos["sl"], lots=pos["lots"],
                           gross=gross, fees=fees, profit=gross-fees,
                           equity_after=balance, reason=reason, fx_used=rate,
                           planned_risk=pos["planned_risk"], entry_balance=pos["entry_balance"],
                           entry_daily_headroom=pos["entry_daily_headroom"],
                           entry_static_headroom=pos["entry_static_headroom"]))
        pos = None
        observe(balance, i)

    def enter(i, price, rate):
        nonlocal balance, pos, first_static_block
        if pos is None and side[i]:
            entry, sl = price+spread+slip, stops[i]
            if sl <= 0 or price <= sl or not np.isfinite(sl):
                return
            loss_per_lot = (entry-sl+slip)*100000/rate+commission
            lots = math.floor(max(0., min(initial_balance/10000., balance*.01/loss_per_lot))*100)/100
            planned_risk = lots*loss_per_lot
            bad_daily = day in daily_guard_days or planned_risk > balance-daily_floor+epsilon
            bad_static = permanent_halt is not None or planned_risk > balance-static_floor+epsilon
            bad_concurrent = planned_risk > initial_balance*.03+epsilon
            bad_min_lot = lots < .01
            if bad_daily or bad_static or bad_concurrent or bad_min_lot:
                blocked["blocked_entries"] += 1
                for key, bad in (("blocked_daily", bad_daily), ("blocked_static", bad_static),
                                 ("blocked_concurrent", bad_concurrent), ("blocked_min_lot", bad_min_lot)):
                    blocked[key] += int(bad)
                if bad_static and first_static_block is None:
                    first_static_block = times[i]
                return
            pos = dict(entry=entry, sl=sl, lots=lots, bar=i, planned_risk=planned_risk,
                       entry_balance=balance, entry_daily_headroom=balance-daily_floor,
                       entry_static_headroom=balance-static_floor)
            balance -= lots*commission/2
            entry_equity = liquidation_equity(price, rate)
            observe(entry_equity, i)
            if entry_equity <= floor+epsilon:
                settle(price-slip, rate, i, "entry_"+guard_reason)

    for i in indices:
        op, _, lo, cl, fx, fx_prev = values[i]
        if day != times[i].date():
            day, day_anchor = times[i].date(), balance
        daily_floor = day_anchor-daily_allowance
        floor = max(daily_floor, static_floor)
        guard_reason = "daily_guard" if daily_floor >= static_floor else "static_guard"
        observe(balance, i)
        if entry_at_open:
            if pos is not None and times[i]-times[pos["bar"]] >= pd.Timedelta(hours=12):
                # Exit on the opening quote, before this candle's high/low.
                reason = "gap_sl" if op <= pos["sl"] else "time"
                settle(op-slip, fx_prev, i, reason)
            enter(i, op, fx_prev)
        if pos is not None:
            # Solve the liquidation-equity floor for an executable bid, reserving
            # exit commission and slippage. The higher long stop executes first.
            guard_price = (pos["entry"]+slip
                           +(floor-balance+pos["lots"]*commission/2)*fx_prev/(100000*pos["lots"]))
            effective_stop = max(pos["sl"], guard_price)
            reason = guard_reason if guard_price >= pos["sl"] else "sl"
            if op <= effective_stop:
                settle(op-slip, fx_prev, i, "gap_"+reason)
            elif lo <= effective_stop:
                settle(effective_stop-slip, fx_prev, i, reason)
            else:
                # The low is reachable while still holding. Never inspect prices
                # below an executed stop. Open-entry mode includes the entry candle.
                observe(liquidation_equity(lo, fx_prev), i)
                close_equity = liquidation_equity(cl, fx)
                observe(close_equity, i)
                if close_equity <= floor+epsilon:
                    settle(cl-slip, fx, i, "close_"+guard_reason)
                elif not entry_at_open and times[i]-times[pos["bar"]] >= pd.Timedelta(hours=12):
                    settle(cl-slip, fx, i, "time")
        if not entry_at_open:
            enter(i, cl, fx)
    if pos is not None:
        i = indices[-1]
        settle(values[i, 3]-slip, values[i, 4], i, "end")
    ledger = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    profit = ledger.profit.astype(float)
    equity = np.r_[initial_balance, ledger.equity_after.to_numpy(dtype=float)]
    assert abs(initial_balance+profit.sum()-balance) < 1e-6
    assert np.allclose(initial_balance+profit.cumsum(), ledger.equity_after.astype(float), atol=1e-6, rtol=0)
    summary = dict(net=float(profit.sum()), final_balance=float(balance), trades=len(ledger),
                   win_rate=float((profit > 0).mean()*100) if len(profit) else 0.,
                   profit_factor=float(profit[profit > 0].sum()/-profit[profit < 0].sum()) if (profit < 0).any() else None,
                   closed_drawdown=float((np.maximum.accumulate(equity)-equity).max()),
                   permanent_halt=permanent_halt, initial_balance=initial_balance,
                   first_static_block=first_static_block, **blocked,
                   daily_guard_days=len(daily_guard_days),
                   internal_daily_breaches=len(internal_daily_days),
                   internal_static_breaches=int(internal_static_breach),
                   firm_daily_breaches=len(firm_daily_days),
                   firm_static_breaches=int(firm_static_breach),
                   min_liquidation_equity=float(min_equity), max_daily_loss=float(max_daily_loss),
                   max_static_loss=float(initial_balance-min_equity),
                   gap_exits=sum(t["reason"].startswith("gap_") for t in trades))
    return summary, ledger
