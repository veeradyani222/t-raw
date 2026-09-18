"""Independently reconcile the saved account-comparison financial ledgers."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'logs/jpy-account-comparison-20260913'


def main():
    payload = json.loads((OUT/'results.json').read_text())
    count = 0
    for r in payload['rows']:
        t = pd.read_csv(OUT/r['ledger'], parse_dates=['entry_time', 'exit_time'])
        initial = r['initial_balance']
        assert len(t)==r['trades']
        if len(t):
            expected_gross = (t['exit']-t.entry)*100000*t.lots/t.fx_used
            expected_fees = t.lots*r['commission_round_trip']
            assert np.allclose(t.gross, expected_gross)
            assert np.allclose(t.fees, expected_fees)
            assert np.allclose(t.profit, expected_gross-expected_fees)
            assert np.allclose(t.equity_after, initial+t.profit.cumsum())
            assert (t.entry_time.dt.hour==0).all()
            assert (t.exit_time>=t.entry_time).all()
            assert (t.entry_time>=pd.Timestamp(r['start'])).all()
            assert (t.exit_time<pd.Timestamp(r['end_exclusive'])).all()
            assert np.allclose(t.lots*100, np.round(t.lots*100))
            assert (t.lots <= initial/10000+1e-9).all()
            assert (t.planned_risk <= t.entry_balance*.01+1e-6).all()
            timed = t[t.reason=='time']
            assert ((timed.exit_time-timed.entry_time) >= pd.Timedelta(hours=12)).all()
            # Monthly realized-net attribution is valid only if no position
            # straddles a month with its entry fee already charged.
            if r['window']=='latest_12_months':
                assert (t.entry_time.dt.to_period('M')==t.exit_time.dt.to_period('M')).all()
            count += len(t)
        assert abs(t.profit.sum()-r['net'])<1e-6
        assert abs(initial+t.profit.sum()-r['final_balance'])<1e-6
        if r['window']=='latest_12_months':
            months = [m for m in payload['months'] if m['symbol']==r['symbol']
                      and m['initial_balance']==initial and m['profile']==r['profile']]
            assert len(months)==12
            balance = float(initial)
            for m in months:
                expected = t.loc[t.exit_time.dt.strftime('%Y-%m')==m['month'], 'profit'].sum()
                assert abs(expected-m['net'])<1e-6
                balance += expected
                assert abs(balance-m['ending_balance'])<1e-6
            assert abs(balance-r['final_balance'])<1e-6
    for a in payload['averages']:
        annual = [r for r in payload['rows'] if r['symbol']==a['symbol']
                  and r['initial_balance']==a['initial_balance'] and r['profile']==a['profile']
                  and r['window'].isdigit()]
        assert len(annual)==10
        assert abs(np.mean([r['net'] for r in annual])-a['mean_net'])<1e-6
    audit = dict(runs=len(payload['rows']), trade_rows=count, annual_means=len(payload['averages']),
                 monthly_rows=len(payload['months']), status='passed')
    (OUT/'verification.json').write_text(json.dumps(audit, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
