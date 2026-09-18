"""Descriptive offline comparison; reads cached prices and existing ledgers only."""
from pathlib import Path

import pandas as pd


def main():
    root = Path(__file__).resolve().parents[1]
    prices = pd.read_csv(root / 'data/session-chfjpy-h1-screen-20260913.csv', parse_dates=['time'])
    folder = root / 'logs/jpy-account-comparison-20260913'
    results = pd.read_csv(folder / 'all-results.csv')
    chosen = results[(results.symbol == 'CHFJPY') & (results.profile == 'base') &
                     (results.initial_balance == 10000)]
    assert len(chosen) == 11 and prices.time.is_monotonic_increasing
    assert not prices.time.duplicated().any()
    rows = []
    for result in chosen.itertuples():
        sample = prices[(prices.time >= pd.Timestamp(result.start)) &
                        (prices.time < pd.Timestamp(result.end_exclusive))]
        ledger = pd.read_csv(folder / result.ledger)
        assert abs(ledger.profit.sum() - result.net) < 1e-6
        rows.append(dict(window=result.window, first_time=sample.time.iloc[0],
                         last_time=sample.time.iloc[-1], first_close=sample.close.iloc[0],
                         last_close=sample.close.iloc[-1],
                         underlying_pct=100 * (sample.close.iloc[-1] / sample.close.iloc[0] - 1),
                         strategy_net=result.net, trades=result.trades,
                         first_static_block=result.first_static_block,
                         last_exit=ledger.exit_time.iloc[-1]))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    main()
