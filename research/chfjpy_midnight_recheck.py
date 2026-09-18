"""Fixed midnight-opening CHFJPY replay; offline, no MT5 connection."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from research.jpy_account_comparison import frames
from research.jpy_guarded_session import simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'logs/chfjpy-midnight-recheck-20260917'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data, audit = frames()
    df = data['CHFJPY']
    windows = [(str(y), pd.Timestamp(y, 1, 1), pd.Timestamp(y+1, 1, 1))
               for y in range(2016, 2026)]
    windows += [('latest_12_months', pd.Timestamp('2025-09-01'), pd.Timestamp('2026-09-01')),
                ('Jul-Aug', pd.Timestamp('2026-07-01'), pd.Timestamp('2026-09-01'))]
    rows, months = [], []
    for mode in ('old_close', 'midnight_open'):
        for profile, spread in (('base', 2.5), ('wide', 5.)):
            for label, start, end in windows:
                summary, trades = simulate(df, start, end, spread_pips=spread,
                                           entry_at_open=mode == 'midnight_open')
                name = f'{mode}-{profile}-{label}'
                trades.to_csv(OUT / f'{name}-trades.csv', index=False)
                assert abs(10000 + trades.profit.sum() - summary['final_balance']) < 1e-6
                if mode == 'midnight_open' and len(trades):
                    assert (trades.entry_time.dt.hour == 0).all()
                    timed = trades[trades.reason == 'time']
                    assert ((timed.exit_time - timed.entry_time) >= pd.Timedelta(hours=12)).all()
                rows.append(dict(mode=mode, profile=profile, window=label, **summary))
                if label in ('Jul-Aug', 'latest_12_months'):
                    for month in pd.date_range(start, end, freq='MS', inclusive='left'):
                        selected = trades[(trades.exit_time >= month) &
                                          (trades.exit_time < month + pd.DateOffset(months=1))]
                        months.append(dict(mode=mode, profile=profile, window=label,
                                           month=str(month.date()), net=float(selected.profit.sum()),
                                           trades=len(selected)))
    results = pd.DataFrame(rows)
    results.to_csv(OUT / 'summary.csv', index=False)
    pd.DataFrame(months).to_csv(OUT / 'monthly.csv', index=False)
    (OUT / 'results.json').write_text(json.dumps(dict(audit=audit, rows=rows, months=months,
        code_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (Path(__file__), ROOT/'research/jpy_guarded_session.py')}),
        indent=2, default=str), encoding='utf-8')
    print(results[['mode', 'profile', 'window', 'net', 'trades', 'first_static_block']].to_string(index=False))
    print(pd.DataFrame(months).query("window == 'Jul-Aug'").to_string(index=False))


if __name__ == '__main__':
    main()
