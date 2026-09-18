"""Offline gold replay of the existing hour-0, 12-hour session hypothesis."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from research.jpy_session_recheck import signal_inputs
from trader.risk import RiskGuard

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'logs/gold-session-recheck-20260913'
COLUMNS = ['entry_time', 'exit_time', 'entry', 'exit', 'sl', 'lots', 'gross',
           'fees', 'profit', 'equity_after', 'reason']


def simulate(df, start, end, *, spread=.30, slip=.03, fee_rate=.000018):
    """Same signal/closed-balance rails as JPY; 100oz gold contract in USD.

    fee_rate is charged on traded notional at each fill. Timestamps identify
    candle opens, although entries and timed exits execute at candle closes.
    """
    side, stops = signal_inputs(df, 0)
    values = df[['open', 'high', 'low', 'close']].to_numpy()
    times = pd.DatetimeIndex(df.time)
    indices = np.flatnonzero((times >= start) & (times < end))
    guard = RiskGuard(1, .03, 0., 10000., .06)
    balance, pos, halt, trades = 10000., None, None, []

    def settle(price, i, reason):
        nonlocal balance, pos
        gross = (price-pos['entry'])*100*pos['lots']
        exit_fee = price*100*pos['lots']*fee_rate
        fees = pos['entry_fee']+exit_fee
        balance += gross-exit_fee
        trades.append(dict(entry_time=times[pos['bar']], exit_time=times[i],
                           entry=pos['entry'], exit=price, sl=pos['sl'],
                           lots=pos['lots'], gross=gross, fees=fees,
                           profit=gross-fees, equity_after=balance, reason=reason))
        pos = None

    for i in indices:
        op, hi, lo, cl = values[i]
        if pos is not None:
            if op <= pos['sl']:
                settle(op-slip, i, 'gap_sl')
            elif lo <= pos['sl']:
                settle(pos['sl']-slip, i, 'sl')
            elif times[i]-times[pos['bar']] >= pd.Timedelta(hours=12):
                settle(cl-slip, i, 'time')
        guard.on_new_bar(times[i].date(), balance)
        if guard.blown and halt is None:
            halt = times[i]
        if pos is None and side[i] and guard.may_open(0)[0]:
            entry, sl = cl+spread+slip, stops[i]
            loss_per_lot = (entry-sl+slip)*100+(entry+sl-slip)*100*fee_rate
            lots = math.floor(min(1., balance*.01/loss_per_lot)*100)/100
            if lots >= .01:
                entry_fee = entry*100*lots*fee_rate
                balance -= entry_fee
                pos = dict(entry=entry, sl=sl, lots=lots, bar=i, entry_fee=entry_fee)
    if pos is not None:
        i = indices[-1]
        settle(values[i, 3]-slip, i, 'end')
    t = pd.DataFrame(trades, columns=COLUMNS)
    p = t.profit.astype(float)
    assert abs(10000+p.sum()-balance) < 1e-6
    assert ((10000+p.cumsum()-t.equity_after.astype(float)).abs() < 1e-6).all()
    eq = np.r_[10000., t.equity_after.to_numpy(dtype=float)]
    return dict(net=float(p.sum()), final_balance=balance, trades=len(t),
                win_rate=float((p>0).mean()*100) if len(t) else None,
                profit_factor=float(p[p>0].sum()/-p[p<0].sum()) if (p<0).any() else None,
                closed_drawdown=float((np.maximum.accumulate(eq)-eq).max()),
                permanent_halt=halt), t


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [ROOT/'data/xauusd-h1.csv', ROOT/'data/session-xauusd-h1-recent-20260913.csv']
    cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume']
    raw = pd.concat([pd.read_csv(p, parse_dates=['time'])[cols] for p in paths])
    # Two isolated 2009 records precede a seven-year gap; they are not usable history.
    discarded = raw[raw.time < '2017-01-01']
    d = raw[raw.time >= '2017-01-01'].drop_duplicates('time', keep='last').sort_values('time').reset_index(drop=True)
    assert d.time.is_monotonic_increasing and not d.time.duplicated().any()
    assert np.isfinite(d[cols[1:]].to_numpy()).all() and (d.tick_volume>0).all()
    assert ((d.high >= d[['open', 'close', 'low']].max(axis=1)) &
            (d.low <= d[['open', 'close', 'high']].min(axis=1))).all()
    audit = dict(first=str(d.time.min()), last=str(d.time.max()), bars=len(d),
                 discarded_isolated_rows=len(discarded),
                 hour0_counts_by_year=d[d.time.dt.hour==0].groupby(d.time.dt.year).size().to_dict(),
                 source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    rows, monthly = [], []
    windows = [(str(y), pd.Timestamp(y, 1, 1), pd.Timestamp(y+1, 1, 1)) for y in range(2018, 2026)]
    windows += [('2026_YTD', pd.Timestamp('2026-01-01'), pd.Timestamp('2026-09-12')),
                ('latest_12_months', pd.Timestamp('2025-09-01'), pd.Timestamp('2026-09-01')),
                ('August_2026_fresh', pd.Timestamp('2026-08-01'), pd.Timestamp('2026-09-01'))]
    for profile, spread in [('base', .30), ('wide_spread', .60)]:
        for label, start, end in windows:
            assert (d.time < start).sum() >= 15
            s, t = simulate(d, start, end, spread=spread)
            rows.append(dict(profile=profile, window=label, start=str(start),
                             end_exclusive=str(end), spread_price=spread, **s))
            t.to_csv(OUT/f'{profile}-{label}-trades.csv', index=False)
            if label == 'latest_12_months':
                balance = 10000.
                for month in pd.date_range(start, end, freq='MS', inclusive='left'):
                    selected = t[(t.exit_time >= month) & (t.exit_time < month+pd.DateOffset(months=1))]
                    gain = float(selected.profit.sum())
                    balance += gain
                    monthly.append(dict(profile=profile, month=f'{month:%Y-%m}', net=gain,
                                        trades=len(selected), balance=balance))
                assert abs(balance-s['final_balance']) < 1e-6
    averages = {}
    for profile in ('base', 'wide_spread'):
        annual = [r for r in rows if r['profile']==profile and r['window'].isdigit()]
        averages[profile] = dict(years=len(annual), mean_net=float(np.mean([r['net'] for r in annual])),
                                 profitable_years=sum(r['net']>0 for r in annual),
                                 zero_trade_years=sum(r['trades']==0 for r in annual),
                                 halted_years=sum(r['permanent_halt'] is not None for r in annual))
    payload = dict(audit=audit, rows=rows, monthly=monthly, averages=averages,
                   config=dict(signal_hour=0, hold_hours=12, stop_atr_multiple=2, atr_period=14,
                               risk=.01, initial_balance=10000, contract_oz=100,
                               commission_notional_per_side=.000018, slippage_price_per_fill=.03),
                   code_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (Path(__file__), ROOT/'research/jpy_session_recheck.py', ROOT/'trader/risk.py')})
    (OUT/'results.json').write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')
    pd.DataFrame(rows).to_csv(OUT/'results.csv', index=False)
    pd.DataFrame(monthly).to_csv(OUT/'monthly.csv', index=False)
    lines = ['# Gold hour-0 / 12-hour exit research - 13 September 2026', '',
             'Exact transfer of the JPY research signal: long only, H1 bar labelled 00:00, enter at its completed close plus spread/slippage, stop at close minus twice the simple ATR14, no TP, close after 12 elapsed hours unless stopped first. With regular bars the entry is around 01:00 and timed exit around 13:00 in dataset clock. This is not a literal midnight order or a verified FundedNext timezone.', '',
             'Gold rarely has an hour-0 bar on this feed. Missing midnight candles produce no entries; no replacement hour was selected or optimized. The 17 eligible candles in the latest 12 months are concentrated in October 2025 and March 2026. Fourteen trades execute; March 20, 23 and 24 are skipped because even 0.01 lot exceeds the 1% risk budget. The seasonal pattern suggests a clock/session-calendar effect, but its cause is not independently verified.', '',
             f"Data: {audit['bars']} H1 bars from {audit['first']} through {audit['last']}. Two isolated 2009 records were excluded. 2017 is used as warmup; eight full calendar years 2018-2025 are reported. Source hashes and annual hour-0 counts are in results.json.", '',
             'Each year independently starts flat at $10,000; the latest-12-month table is one continuous $10,000 account with no withdrawals. Target risk 1% of balance including estimated stopped-trade costs, max 1 lot, 0.01 step, 100oz/lot. Existing 3% daily / 6% static CLOSED-BALANCE guards: no new trades after a total halt. Gaps fill at opening price less slippage; stop takes priority over timed exit.', '',
             'Cost scenarios: $0.30 or $0.60 price spread (3 or 6 gold pips at $0.10/pip), $0.03 slippage per fill, commission 0.0018% of notional on EACH side. This deliberately models the literal Stellar Lite general-page wording; it is not verified against a FundedNext account ledger. [FundedNext published conditions](https://fundednext.com/general-rules/cfds/symbols-and-conditions). Local terminal is MetaQuotes-Demo, not FundedNext. These costs are applied to all historical years to assess the strategy under this assumed current cost profile.', '',
             'No swap, funded news-profit adjustment, intrabar floating-equity enforcement, margin model or FundedNext timezone mapping. Results do not certify prop-rule compliance or predict payouts. Trade ledger timestamps are bar labels, not exact fill timestamps. Live BOS code and strategy registry were not changed.', '',
             '## Calendar years', '', '| Year | Base net | Trades | Wide-spread net |', '|---|---:|---:|---:|']
    for year in range(2018, 2026):
        a, b = [next(r for r in rows if r['profile']==p and r['window']==str(year)) for p in ('base', 'wide_spread')]
        lines.append(f"| {year} | ${a['net']:+.2f} | {a['trades']} | ${b['net']:+.2f} |")
    lines += ['', f"Mean annual base profit: ${averages['base']['mean_net']:+.2f}, including zero-trade years. Full summary: `{averages}`.", '',
              '## Latest 12 complete months: September 2025-August 2026', '',
              '| Month | Base net | Trades | Ending balance |', '|---|---:|---:|---:|']
    for r in monthly:
        if r['profile']=='base':
            lines.append(f"| {r['month']} | ${r['net']:+.2f} | {r['trades']} | ${r['balance']:.2f} |")
    lines += ['', '## Window summaries', '', '| Window | Profile | Net | Trades | Win rate | Closed DD | Halt |', '|---|---|---:|---:|---:|---:|---|']
    for r in rows:
        if not r['window'].isdigit():
            win = '-' if r['win_rate'] is None else f"{r['win_rate']:.2f}%"
            lines.append(f"| {r['window']} | {r['profile']} | ${r['net']:+.2f} | {r['trades']} | {win} | ${r['closed_drawdown']:.2f} | {r['permanent_halt']} |")
    (ROOT/'docs/2026-09-13-gold-session-results.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(pd.DataFrame(rows)[['profile', 'window', 'net', 'trades', 'win_rate', 'permanent_halt']].to_string(index=False))
    print(json.dumps(averages, indent=2))


if __name__ == '__main__':
    main()
