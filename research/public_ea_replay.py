"""Offline analytical replay of three published rule sets, not executable EAs.

Source references and deviations: docs/2026-09-17-public-ea-candidates.md.
No terminal, network, orders, parameter search, or live registration.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'logs/public-ea-replay-20260917'
SPECS = {'adjustable_ma': 'H1', 'rsi': 'H1', 'heiken_ashi': 'D1'}


def rsi(close, period=14):
    delta = close.diff().to_numpy(float)
    result = np.full(len(close), np.nan)
    if len(close) <= period:
        return pd.Series(result, index=close.index)
    gain = np.maximum(delta[1:period+1], 0).mean()
    loss = np.maximum(-delta[1:period+1], 0).mean()
    for i in range(period, len(close)):
        if i > period:
            gain = (gain*(period-1)+max(delta[i], 0))/period
            loss = (loss*(period-1)+max(-delta[i], 0))/period
        result[i] = 100-100/(1+gain/loss) if loss else (100 if gain else 50)
    return pd.Series(result, index=close.index)


def signals(df, name):
    """Requests on completed bars; execution must wait until the next open."""
    n = len(df)
    entry = np.zeros(n, dtype=int)
    if name == 'adjustable_ma':
        difference = (df.close.ewm(span=20, adjust=False).mean()
                      - df.close.ewm(span=22, adjust=False).mean()).to_numpy()
        state = 0
        for i in range(22, n):
            direction = 1 if difference[i] >= .00003 else (-1 if difference[i] <= -.00003 else 0)
            if direction:
                if state and direction != state:
                    entry[i] = direction
                state = direction
        exit_long, exit_short = entry == -1, entry == 1
    elif name == 'rsi':
        value = rsi(df.close)
        entry[(value > 20) & (value.shift() <= 20)] = 1
        entry[(value < 80) & (value.shift() >= 80)] = -1
        exit_long, exit_short = entry == -1, entry == 1
    elif name == 'heiken_ashi':
        ha_open = np.zeros(n)
        ha_close = df[['open', 'high', 'low', 'close']].mean(axis=1).to_numpy(copy=True)
        if n:
            ha_open[0], ha_close[0] = df.open.iloc[0], df.close.iloc[0]
        for i in range(1, n):
            ha_open[i] = (ha_open[i-1]+ha_close[i-1])/2
        body = ha_close-ha_open
        previous = np.r_[0., body[:-1]] if n else np.array([])
        bullish = (body > 0) & (previous > 0) & (df.low.to_numpy() >= ha_open)
        bearish = (body < 0) & (previous < 0) & (df.high.to_numpy() <= ha_open)
        entry[bullish & (body > abs(previous))] = -1  # Published Inverted=true.
        entry[bearish & (-body > abs(previous))] = 1
        exit_long, exit_short = bullish, bearish
    else:
        raise ValueError(name)
    return pd.DataFrame(dict(entry=entry, exit_long=exit_long, exit_short=exit_short), index=df.index)


def simulate(df, requests, start, end, *, spread_pips=1., commission=14., slip_pips=.1):
    """EURUSD, USD account, 0.1 fixed lot, default no stop and no risk overlay.

The $600 threshold is diagnostic, not an invented liquidation or entry halt.
Intrabar peak-to-trough drawdown is a conservative OHLC upper bound.
"""
    times = pd.DatetimeIndex(df.time)
    assert times.is_monotonic_increasing and not times.has_duplicates
    values = df[['open', 'high', 'low', 'close']].to_numpy(float)
    assert np.isfinite(values).all()
    assert (values[:, 1] >= values[:, [0, 2, 3]].max(axis=1)).all()
    assert (values[:, 2] <= values[:, [0, 1, 3]].min(axis=1)).all()
    instructions = requests[['entry', 'exit_long', 'exit_short']].to_numpy()
    indices = np.flatnonzero((times >= pd.Timestamp(start)) & (times < pd.Timestamp(end)))
    spread, slip = spread_pips*.0001, slip_pips*.0001
    units, fee = 10000., commission*.1/2
    balance = peak = minimum = 10000.
    max_dd = 0.
    pos = None
    trades = []

    def executable(bid, side):
        return bid + (spread if side == -1 else 0) - side*slip

    def mark(bid):
        if pos is None:
            return balance
        return balance + pos['side']*(executable(bid, pos['side'])-pos['entry'])*units-fee

    def settle(bid, stamp, reason):
        nonlocal balance, pos
        price = executable(bid, pos['side'])
        gross = pos['side']*(price-pos['entry'])*units
        balance += gross-fee
        trades.append(dict(entry_time=pos['time'], exit_time=stamp, side=pos['side'],
                           entry=pos['entry'], exit=price, lots=.1, gross=gross,
                           fees=2*fee, profit=gross-2*fee, equity_after=balance, reason=reason))
        pos = None

    for i in indices:
        op, hi, lo, cl = values[i]
        if i > 0:
            entry, exit_long, exit_short = instructions[i-1]
            if pos is not None and ((pos['side'] == 1 and exit_long)
                                    or (pos['side'] == -1 and exit_short)):
                settle(op, times[i], 'signal')
            if pos is None and entry:
                side = int(entry)
                pos = dict(side=side, time=times[i], entry=op+(spread if side == 1 else 0)+side*slip)
                balance -= fee
        if pos is not None:
            adverse, favorable = (lo, hi) if pos['side'] == 1 else (hi, lo)
            peak = max(peak, mark(favorable))
            minimum = min(minimum, mark(adverse))
            max_dd = max(max_dd, peak-mark(adverse))
        else:
            peak, minimum = max(peak, balance), min(minimum, balance)
            max_dd = max(max_dd, peak-balance)
    if pos is not None:
        i = indices[-1]
        # Forced final close; timestamp labels this final bar, not an exact tick.
        settle(values[i, 3], times[i], 'end')
    ledger = pd.DataFrame(trades, columns=['entry_time', 'exit_time', 'side', 'entry', 'exit',
                                         'lots', 'gross', 'fees', 'profit', 'equity_after', 'reason'])
    profit = ledger.profit.astype(float)
    assert abs(10000+profit.sum()-balance) < 1e-6
    assert np.allclose(10000+profit.cumsum(), ledger.equity_after.astype(float), atol=1e-6)
    return dict(net=float(profit.sum()), final_balance=balance, trades=len(ledger),
                wins=int((profit > 0).sum()), losses=int((profit < 0).sum()),
                max_drawdown_upper_bound=max_dd, min_equity=minimum,
                static_600_breached=bool(minimum <= 9400)), ledger


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, months, audit = [], [], {}
    windows = [(str(y), f'{y}-01-01', f'{y+1}-01-01') for y in range(2018, 2026)]
    windows += [('last_12_complete_months', '2025-08-01', '2026-08-01'),
                ('July_August_partial', '2026-07-01', '2026-08-22')]
    for name, timeframe in SPECS.items():
        path = ROOT / f'data/eurusd-{timeframe.lower()}.csv'
        df = pd.read_csv(path, parse_dates=['time'])
        request = signals(df, name)
        audit[name] = dict(source=str(path.relative_to(ROOT)),
                           sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           first=str(df.time.min()), last=str(df.time.max()), timeframe=timeframe)
        for profile, spread in [('base', 1.), ('wide', 2.)]:
            for label, start, end in windows:
                result, trades = simulate(df, request, start, end, spread_pips=spread)
                rows.append(dict(candidate=name, timeframe=timeframe, profile=profile, window=label, **result))
                trades.to_csv(OUT/f'{name}-{profile}-{label}-trades.csv', index=False)
                if label == 'July_August_partial':
                    for month, until in [('2026-07-01', '2026-08-01'), ('2026-08-01', '2026-08-22')]:
                        chosen = trades[(trades.exit_time >= month)&(trades.exit_time < until)]
                        months.append(dict(candidate=name, profile=profile, month=month,
                                           end_exclusive=until, net=float(chosen.profit.sum()), trades=len(chosen)))
    pd.DataFrame(rows).to_csv(OUT/'summary.csv', index=False)
    pd.DataFrame(months).to_csv(OUT/'monthly.csv', index=False)
    (OUT/'results.json').write_text(json.dumps(dict(rows=rows, months=months, audit=audit,
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2), encoding='utf-8')
    print(pd.DataFrame(rows).query("profile == 'base'").to_string(index=False))


if __name__ == '__main__':
    main()
