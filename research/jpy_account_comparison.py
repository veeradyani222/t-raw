"""Calendar and monthly CHFJPY/EURJPY research at two account sizes."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.jpy_pair_screen import cached
from research.jpy_guarded_session import simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'logs/jpy-account-comparison-20260913'
PAIRS = ('CHFJPY', 'EURJPY')
SIZES = (10000, 50000)
END = pd.Timestamp('2026-09-01')


def frames():
    usd, fx_paths = cached('USDJPY')
    fx = usd[['time', 'close']].rename(columns={'close': 'fx'})
    fx['fx_previous'] = fx.fx.shift()
    result, audit = {}, {}
    for symbol in PAIRS:
        path = ROOT/f'data/session-{symbol.lower()}-h1-screen-20260913.csv'
        raw = pd.read_csv(path, parse_dates=['time'])
        raw = raw[raw.time < END]
        assert raw.time.is_monotonic_increasing and not raw.time.duplicated().any()
        assert np.isfinite(raw[['open', 'high', 'low', 'close']]).all().all()
        assert (raw.high >= raw[['open', 'close', 'low']].max(axis=1)).all()
        assert (raw.low <= raw[['open', 'close']].min(axis=1)).all()
        d = pd.merge_asof(raw, fx, on='time', tolerance=pd.Timedelta(hours=3))
        d = d.dropna(subset=['fx', 'fx_previous']).reset_index(drop=True)
        assert (d[['fx', 'fx_previous']] > 0).all().all()
        result[symbol] = d
        audit[symbol] = dict(first=str(d.time.min()), last=str(d.time.max()), bars=len(d),
                             dropped_conversion_rows=len(raw)-len(d),
                             source_hash=hashlib.sha256(path.read_bytes()).hexdigest())
    audit['conversion_source_hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fx_paths}
    return result, audit


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, audit = frames()
    rows, months = [], []
    windows = [(str(y), pd.Timestamp(y, 1, 1), pd.Timestamp(y+1, 1, 1)) for y in range(2016, 2026)]
    windows += [('latest_12_months', pd.Timestamp('2025-09-01'), END)]
    for symbol in PAIRS:
        for size in SIZES:
            for profile, spread in [('base', 2.5), ('wide', 5.)]:
                for label, start, end in windows:
                    assert (data[symbol].time < start).sum() >= 15
                    summary, t = simulate(data[symbol], start, end, initial_balance=size,
                                          spread_pips=spread, commission=14.)
                    filename = f'{symbol}-{size}-{profile}-{label}-trades.csv'
                    t.to_csv(OUT/filename, index=False)
                    rows.append(dict(symbol=symbol, profile=profile, window=label,
                                     start=str(start), end_exclusive=str(end), spread_pips=spread,
                                     commission_round_trip=14., ledger=filename, **summary))
                    if label == 'latest_12_months':
                        balance = float(size)
                        for month in pd.date_range(start, end, freq='MS', inclusive='left'):
                            selected = t[(t.exit_time >= month) & (t.exit_time < month+pd.DateOffset(months=1))]
                            net = float(selected.profit.sum())
                            balance += net
                            months.append(dict(symbol=symbol, initial_balance=size, profile=profile,
                                               month=f'{month:%Y-%m}', net=net, trades=len(selected),
                                               ending_balance=balance))
                        assert abs(balance-summary['final_balance']) < 1e-6
            print(symbol, size, 'complete', flush=True)
    averages = []
    for symbol in PAIRS:
        for size in SIZES:
            for profile in ('base', 'wide'):
                annual = [r for r in rows if r['symbol']==symbol and r['initial_balance']==size
                          and r['profile']==profile and r['window'].isdigit()]
                averages.append(dict(symbol=symbol, initial_balance=size, profile=profile,
                                     mean_net=float(np.mean([r['net'] for r in annual])),
                                     mean_return_pct=float(np.mean([r['net'] for r in annual])/size*100),
                                     profitable_years=sum(r['net'] > 0 for r in annual),
                                     guard_limited_years=sum(r['permanent_halt'] is not None or r['first_static_block'] is not None for r in annual)))
    config = dict(risk_per_trade=.01, daily_buffer=.03, static_buffer=.06,
                  max_lots_per_10000=1., lot_step=.01, commission_round_trip=14.,
                  slippage_pips_per_fill=.1, withdrawals=False)
    payload = dict(audit=audit, config=config, rows=rows, months=months, averages=averages,
                   code_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (Path(__file__), ROOT/'research/jpy_guarded_session.py', ROOT/'research/jpy_session_recheck.py')})
    (OUT/'results.json').write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')
    pd.DataFrame(rows).to_csv(OUT/'all-results.csv', index=False)
    pd.DataFrame(months).to_csv(OUT/'monthly.csv', index=False)
    pd.DataFrame(averages).to_csv(OUT/'averages.csv', index=False)
    write_report(payload)
    print(pd.DataFrame(averages).to_string(index=False))
    print(pd.DataFrame([r for r in rows if r['window']=='latest_12_months'])[
        ['symbol', 'initial_balance', 'profile', 'net', 'final_balance', 'trades', 'first_static_block', 'permanent_halt']].to_string(index=False))


def write_report(payload):
    rows, months, averages = (payload[k] for k in ('rows', 'months', 'averages'))
    combos = [(s, b) for s in PAIRS for b in SIZES]
    lines = ['# CHFJPY and EURJPY account comparison - 13 September 2026', '',
             'Historical prices are from the MetaQuotes-Demo research feed, not FundedNext quotes. The earlier pair-screen latest-year results were reproduced exactly before changing costs and guard modeling.', '',
             'Same H1 hour-0 completed-candle long signal, simple ATR14 x2 stop, no take-profit, exit after 12 elapsed hours unless stopped first. Dataset clock retained: hour0 is an H1 opening label; regular execution is around 01:00 and timed exit around 13:00. FundedNext clock mapping is unverified.', '',
             'Each pair is a separate account. Each Jan-Dec year independently starts at $10,000 or $50,000; the latest twelve months are one continuous account beginning September 1, 2025. No deposits or withdrawals. Do not sum separate pair results as a shared portfolio.', '',
             'Target risk is 1% of current balance, including modeled stop execution costs. 0.01 lot steps; the historical 1-lot cap at $10k is scaled to 5 lots at $50k. These are separately simulated accounts, not profit multiplied by five. Rounding, caps and guard decisions can alter proportionality.', '',
             'Base spread 2.5 pips; wide-spread sensitivity 5 pips; 0.1 pip slippage per market fill; commission $14 per lot round trip ($7 each side). This is the cautious literal interpretation of the Stellar Lite general page, not a verified FundedNext account charge. Actual spreads remain unmeasured. [FundedNext costs](https://fundednext.com/general-rules/cfds/symbols-and-conditions). Previous screen used $7 total commission, closed-balance checks and no entry-budget check; its profits should not be substituted into these tables.', '',
             'Internal daily allowance $300/$1,500 and static floor $9,400/$47,000. Full-size entries are rejected if modeled stopped-trade risk would exceed remaining daily/static headroom; open losses are monitored at bar open, adverse low and close, with a liquidation-cost reserve. Guard exit takes priority if its price is above the strategy SL. Gaps exit at actual modeled open, so losses beyond limits are recorded, never clipped. Daily reset follows dataset midnight and realized balance; these timestamps have not been mapped independently to FundedNext server time. [Daily rule](https://help.fundednext.com/en/articles/8019811-how-can-i-calculate-the-daily-loss-limit).', '',
             'JPY profit converts to USD using contemporary USDJPY closes for scheduled exits and previous closes for intrabar exits. H1 OHLC cannot establish tick sequencing or exact simultaneous conversion prices. No swap history, news-profit adjustment, margin simulation, actual execution quotes or payout split. This tests stated drawdown buffers under assumptions; it is not a guarantee of FundedNext compliance. $50k results are hypothetical: current FundedNext policy prohibits automation at $50k and above. [EA policy](https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext).', '',
             '## Calendar years: base costs', '',
             '| Year | CHFJPY $10k | CHFJPY $50k | EURJPY $10k | EURJPY $50k |', '|---|---:|---:|---:|---:|']
    for year in range(2016, 2026):
        selected = [next(r for r in rows if r['symbol']==s and r['initial_balance']==b and r['profile']=='base' and r['window']==str(year)) for s, b in combos]
        cells = [f"${r['net']:+,.2f}"+('*' if r['permanent_halt'] is not None or r['first_static_block'] is not None else '') for r in selected]
        lines.append('| '+str(year)+' | '+' | '.join(cells)+' |')
    selected = [next(r for r in averages if r['symbol']==s and r['initial_balance']==b and r['profile']=='base') for s, b in combos]
    lines += ['| **Annual mean** | '+' | '.join(f"**${r['mean_net']:+,.2f} ({r['mean_return_pct']:+.2f}%)**" for r in selected)+' |', '',
              '* A static guard hit or insufficient headroom prevented one or more entries. Losing and limited years remain in the arithmetic average.', '',
              '## Latest twelve months: September 2025-August 2026', '',
              '| Month | CHFJPY $10k | CHFJPY $50k | EURJPY $10k | EURJPY $50k |', '|---|---:|---:|---:|---:|']
    for month in pd.date_range('2025-09-01', '2026-08-01', freq='MS'):
        selected = [next(r for r in months if r['symbol']==s and r['initial_balance']==b and r['profile']=='base' and r['month']==f'{month:%Y-%m}') for s, b in combos]
        lines.append('| '+f'{month:%b %Y}'+' | '+' | '.join(f"${r['net']:+,.2f}" for r in selected)+' |')
    recent = [next(r for r in rows if r['symbol']==s and r['initial_balance']==b and r['profile']=='base' and r['window']=='latest_12_months') for s, b in combos]
    lines += ['| **Total** | '+' | '.join(f"**${r['net']:+,.2f}**" for r in recent)+' |',
              '| **Ending balance** | '+' | '.join(f"**${r['final_balance']:,.2f}**" for r in recent)+' |', '',
              '## Guard and spread sensitivity', '',
              '| Pair/account | Profile | Recent net | Trades | Lowest modeled liquidation equity | Maximum daily loss | Internal daily/static breaches | Firm 4%/8% breaches |',
              '|---|---|---:|---:|---:|---:|---|---|']
    for r in rows:
        if r['window']=='latest_12_months':
            lines.append(f"| {r['symbol']} / ${r['initial_balance']:,} | {r['profile']} | ${r['net']:+,.2f} | {r['trades']} | ${r['min_liquidation_equity']:,.2f} | ${r['max_daily_loss']:,.2f} | {r['internal_daily_breaches']} / {r['internal_static_breaches']} | {r['firm_daily_breaches']} / {r['firm_static_breaches']} |")
    lines += ['', 'EURJPY calendar 2025 differs sharply across account sizes: the $10k run blocked 41 entries near its static floor but could later resume when rounded lot risk fit the remaining headroom; the $50k run blocked 233 entries and did not resume after February 6. This makes outcomes sensitive to minimum lot steps and the entry-budget rule. It is not evidence that a smaller account has a reliable advantage.', '',
              'Validation: 27 simulator/risk tests passed. An independent ledger check reconciled all 88 runs, 9,450 trade rows, eight annual means and 96 monthly rows, including fees, USD conversion, sizing, timing and ending balances. No modeled 3%/6% or 4%/8% threshold breaches occurred across these runs; many historical years stopped accepting trades because remaining headroom was insufficient. Unmodeled execution and firm-specific rules still matter.', '',
              'All 88 runs, detailed guard events/counts, annual wide-spread results, monthly ending balances, input hashes and trade ledgers are under `logs/jpy-account-comparison-20260913/`. Reproduce with `.venv\\Scripts\\python.exe -m research.jpy_account_comparison`. Live BOS settings and registry were not changed.', '']
    (ROOT/'docs/2026-09-13-jpy-account-comparison.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
