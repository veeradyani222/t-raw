"""Continuous three-year comparison, using the existing guarded research model."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.jpy_account_comparison import frames
from research.jpy_guarded_session import simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'logs/chfjpy-three-year-20260917'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, audit = frames()
    start, end = pd.Timestamp('2023-09-01'), pd.Timestamp('2026-09-01')
    rows, periods = [], []
    for mode in ('old_close', 'midnight_open'):
        for profile, spread in (('base', 2.5), ('wide', 5.)):
            summary, trades = simulate(data['CHFJPY'], start, end,
                                       spread_pips=spread, entry_at_open=mode == 'midnight_open')
            assert abs(trades.profit.sum() - summary['net']) < 1e-6
            assert np.allclose(10000 + trades.profit.cumsum(), trades.equity_after)
            trades.to_csv(OUT / f'{mode}-{profile}-trades.csv', index=False)
            rows.append(dict(mode=mode, profile=profile, **summary))
            balance = 10000.
            for year in range(2023, 2026):
                a, b = pd.Timestamp(year, 9, 1), pd.Timestamp(year+1, 9, 1)
                selected = trades[(trades.exit_time >= a) & (trades.exit_time < b)]
                net = float(selected.profit.sum())
                periods.append(dict(mode=mode, profile=profile, start=str(a.date()),
                                    end_exclusive=str(b.date()), starting_balance=balance,
                                    net=net, ending_balance=balance+net, trades=len(selected)))
                balance += net
            assert abs(balance-summary['final_balance']) < 1e-6
    payload = dict(start=str(start), end_exclusive=str(end), audit=audit, rows=rows,
                   periods=periods, code_hashes={str(p.relative_to(ROOT)):
                   hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (Path(__file__), ROOT/'research/jpy_guarded_session.py')})
    (OUT/'results.json').write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')
    pd.DataFrame(rows).to_csv(OUT/'summary.csv', index=False)
    pd.DataFrame(periods).to_csv(OUT/'annual-periods.csv', index=False)
    print(pd.DataFrame(rows)[['mode','profile','net','final_balance','trades',
                            'closed_drawdown','permanent_halt','first_static_block']].to_string(index=False))
    print(pd.DataFrame(periods).to_string(index=False))


if __name__ == '__main__':
    main()
