"""Offline replay of the former USDJPY hour-6 long session rule."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.jpy_pair_screen import cached
from research.jpy_session_recheck import simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'logs/usdjpy-hour6-recheck-20260917'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df, paths = cached('USDJPY')
    df['fx'] = df.close
    df['fx_previous'] = df.close.shift()
    df = df.dropna(subset=['fx_previous']).reset_index(drop=True)
    assert df.time.is_monotonic_increasing and not df.time.duplicated().any()
    assert np.isfinite(df[['open', 'high', 'low', 'close', 'fx', 'fx_previous']]).all().all()
    assert (df.high >= df[['open', 'low', 'close']].max(axis=1)).all()
    assert (df.low <= df[['open', 'high', 'close']].min(axis=1)).all()
    windows = [(str(y), f'{y}-01-01', f'{y+1}-01-01') for y in range(2016, 2026)]
    windows += [('latest-12-months', '2025-09-01', '2026-09-01'),
                ('Jul-Aug', '2026-07-01', '2026-09-01'),
                ('July-fresh', '2026-07-01', '2026-08-01'),
                ('August-fresh', '2026-08-01', '2026-09-01')]
    previous = json.loads((ROOT / 'logs/jpy-session-history-20260913/results.json').read_text())
    rows, months = [], []
    for profile, commission in [('historical-fee7', 7.), ('fee14', 14.)]:
        for label, start, end in windows:
            start, end = pd.Timestamp(start), pd.Timestamp(end)
            assert (df.time < start).sum() >= 15
            summary, trades = simulate(df, 'USDJPY', 6, start, end,
                                       spread_pips=1., commission=commission, slip_pips=.1)
            p = trades.profit
            assert np.allclose(p, trades.gross - trades.fees)
            assert np.allclose(trades.gross,
                               (trades.exit - trades.entry) * 100000 * trades.lots / trades.exit)
            assert abs(10000 + p.sum() - summary['final_balance']) < 1e-6
            row = dict(profile=profile, window=label, start=str(start), end_exclusive=str(end),
                       commission_round_trip=commission, wins=int((p > 0).sum()),
                       losses=int((p < 0).sum()), **summary)
            if profile == 'historical-fee7' and label.isdigit():
                prior = next(x for x in previous['results'] if x['symbol'] == 'USDJPY'
                             and x['category'] == 'calendar_year' and x['label'] == label)
                assert row['trades'] == prior['trades'] and abs(row['net'] - prior['net']) < 1e-6
            trades.to_csv(OUT / f'{profile}-{label}-trades.csv', index=False)
            rows.append(row)
            if label == 'Jul-Aug':
                for month in ('2026-07', '2026-08'):
                    selected = trades[trades.exit_time.dt.strftime('%Y-%m') == month]
                    months.append(dict(profile=profile, month=month, trades=len(selected),
                                       wins=int((selected.profit > 0).sum()),
                                       losses=int((selected.profit < 0).sum()), net=float(selected.profit.sum())))
                assert abs(sum(x['net'] for x in months if x['profile'] == profile) - summary['net']) < 1e-6
    averages = {}
    for profile in ('historical-fee7', 'fee14'):
        annual = [r for r in rows if r['profile'] == profile and r['window'].isdigit()]
        averages[profile] = dict(mean_net=float(np.mean([r['net'] for r in annual])),
                                 profitable_years=sum(r['net'] > 0 for r in annual),
                                 halted_years=sum(r['permanent_halt'] is not None for r in annual))
    payload = dict(rows=rows, months=months, averages=averages,
                   source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in paths + [Path(__file__), ROOT/'research/jpy_session_recheck.py', ROOT/'trader/risk.py']})
    (OUT / 'results.json').write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')
    pd.DataFrame(rows).to_csv(OUT / 'summary.csv', index=False)
    pd.DataFrame(months).to_csv(OUT / 'monthly.csv', index=False)
    lines = ['# USDJPY hour-6 long session recheck - 17 September 2026', '',
             'Offline replay of the former USDJPY session signal: completed H1 bar labelled 06:00, long entry normally near 07:00 broker/data time, ATR14 x2 stop, no TP, exit 12 elapsed hours after entry (normally near 19:00) unless stopped. The elapsed-time replay follows the existing September13 study; timestamps in the ledger are bar labels, not exact fill times. No session-timezone/DST mapping to Tokyo is independently verified.', '',
             'Every run starts flat with $10,000, 1% balance risk, maximum1 lot and 0.01 lot steps, $300 daily / $600 static closed-balance entry halts. July-August is one continuous account; fresh months and calendar years are separate starts. The model does not liquidate at risk thresholds. A permanent halt explains subsequent months with no trades.', '',
             'Both profiles assume 1-pip spread and 0.1-pip slippage per market fill. historical-fee7 uses $7/lot round-trip commission to reproduce the prior study; fee14 uses the more cautious $14/lot assumption used in later CHFJPY work. Neither fee is verified against account execution records. USDJPY profit converts using exit price. Swap, conversion spread, margin and tick sequencing are not modeled. Different risk engines prevent treating this as a fully controlled comparison with the guarded CHFJPY replay.', '',
             '## July-August continuous account', '',
             '| Commission/lot round trip | July P/L | August P/L | Total P/L | Trades | Wins / losses | Ending balance |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for profile in ('historical-fee7', 'fee14'):
        r = next(x for x in rows if x['profile'] == profile and x['window'] == 'Jul-Aug')
        m = [x for x in months if x['profile'] == profile]
        lines.append(f"| ${r['commission_round_trip']:.0f} | ${m[0]['net']:+.2f} | ${m[1]['net']:+.2f} | ${r['net']:+.2f} | {r['trades']} | {r['wins']} / {r['losses']} | ${r['final_balance']:.2f} |")
    lines += ['', '## Calendar years and latest full twelve months', '',
              '| Window | $7 commission net | $14 commission net |', '|---|---:|---:|']
    for label, _, _ in windows:
        if label == 'Jul-Aug':
            continue
        r = [next(x for x in rows if x['profile'] == profile and x['window'] == label)
             for profile in ('historical-fee7', 'fee14')]
        lines.append(f"| {label} | ${r[0]['net']:+.2f} | ${r[1]['net']:+.2f} |")
    lines += ['', f'Annual averages and halt counts: `{averages}`.', '',
              'All ten historical-fee7 annual results reproduced the saved September13 counts and net profits. All 28 runs reconcile gross P/L, fees, converted P/L and ending balances. Monthly splits reconcile to their continuous runs. This is a replay of cached research-feed prices, not a statement of actual account earnings.', '',
              'Reproduce with `.venv/Scripts/python -m research.usdjpy_hour6_recheck`. [Trade ledgers and manifest](../logs/usdjpy-hour6-recheck-20260917/). [Earlier study](2026-09-13-jpy-session-history.md). No live strategy settings or orders were changed.', '']
    (ROOT / 'docs/2026-09-17-usdjpy-hour6-results.md').write_text('\n'.join(lines), encoding='utf-8')
    print(pd.DataFrame(rows)[['profile', 'window', 'net', 'trades', 'wins', 'losses', 'permanent_halt']].to_string(index=False))
    print(pd.DataFrame(months).to_string(index=False))
    print(averages)


if __name__ == '__main__':
    main()
