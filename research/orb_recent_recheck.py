"""Offline replay of the archived deployed ORB; never restore it to live registry."""
import ast
from dataclasses import asdict, replace
import hashlib
import json
import logging
from pathlib import Path
import subprocess
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from run_live import GOLD
from trader.engine import on_bar
from trader.risk import RiskGuard
from trader.sim import SimBroker
from trader.strategies import bos
from research.jpy_account_comparison import frames
from research.jpy_guarded_session import simulate as jpy_simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'logs/orb-recent-recheck-20260917'
COMMIT = '665430a'
START = pd.Timestamp('2026-07-01')
END = pd.Timestamp('2026-09-01')


def archive(path):
    return subprocess.check_output(['git', 'show', f'{COMMIT}:{path}'], cwd=ROOT).decode('utf-8')


def archived_orb():
    """Recover literal defaults/overrides without importing archived credentials."""
    defaults = {}
    tree = ast.parse(archive('trader/config.py'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Config')
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and (node.target.id.startswith('orb_')
                or node.target.id in ('min_lot', 'max_lot', 'max_drawdown_halt')):
            defaults[node.target.id] = ast.literal_eval(node.value)
    live_tree = ast.parse(archive('run_live.py'))
    call = next(n.value for n in live_tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'GOLD' for t in n.targets))
    values = {k: v for k, v in asdict(GOLD).items() if not k.startswith(('mt5_', 'telegram_'))}
    values.update(defaults)
    rails = next(n.value for n in live_tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'RAILS' for t in n.targets))
    values.update({k.arg: ast.literal_eval(k.value) for k in rails.keywords})
    values.update({k.arg: ast.literal_eval(k.value) for k in call.keywords if k.arg is not None})
    source = archive('trader/strategies/orb.py')
    module = ModuleType('archived_orb')
    exec(compile(source.replace('from ..strategy import', 'from trader.strategy import'),
                 f'{COMMIT}:trader/strategies/orb.py', 'exec'), module.__dict__)
    return module, SimpleNamespace(**values), hashlib.sha256(source.encode()).hexdigest()


def load_bars(path):
    d = pd.read_csv(path, parse_dates=['time'])
    assert d.time.is_monotonic_increasing and not d.time.duplicated().any()
    assert np.isfinite(d[['open', 'high', 'low', 'close']].to_numpy()).all()
    assert (d.high >= d[['open', 'low', 'close']].max(axis=1)).all()
    assert (d.low <= d[['open', 'high', 'close']].min(axis=1)).all()
    assert d.time.min() < START - pd.Timedelta(days=90)
    assert d.time.max() >= END
    return d


def stats(trades):
    p = trades.profit.astype(float)
    curve = np.r_[10000., 10000. + p.cumsum().to_numpy()]
    return dict(trades=len(p), wins=int((p > 0).sum()), losses=int((p < 0).sum()),
                net=float(p.sum()), final_balance=float(curve[-1]),
                win_rate=float(100 * (p > 0).mean()) if len(p) else 0.,
                closed_drawdown=float((np.maximum.accumulate(curve) - curve).max()))


def gold_replay(df, cfg, strategy, start, end):
    broker = SimBroker(df, cfg, 10000.)
    guard = RiskGuard(cfg.max_open_positions, cfg.daily_loss_halt,
                      cfg.max_drawdown_halt, cfg.loss_baseline, cfg.total_loss_halt)
    indices = np.flatnonzero((df.time >= start) & (df.time < end))
    assert len(indices) and indices[0] >= strategy.lookback(cfg)
    halt = None
    with patch('trader.engine.get_strategy', return_value=strategy):
        for i in indices:
            broker.cursor = int(i)
            broker.check_stops()
            event = on_bar(broker, guard, cfg)
            if guard.blown and halt is None:
                halt = df.time.iloc[i]
            if event is not None:
                if event['kind'] == 'open':
                    broker.attach_meta(event['ticket'], event.get('meta', {}))
                else:
                    broker.events.append(event)
        for pos in list(broker.positions):
            broker._settle(pos, df.close.iloc[indices[-1]], 'end')
    trades = pd.DataFrame(broker.trades).rename(columns={'time': 'exit_time'})
    if trades.empty:
        trades = pd.DataFrame(columns=['entry_time', 'exit_time', 'profit', 'equity_after'])
    assert abs(10000. + trades.profit.sum() - broker.equity()) < 1e-6
    assert np.allclose(10000. + trades.profit.cumsum(), trades.equity_after)
    return dict(**stats(trades), permanent_halt=halt), trades, broker.events


def write_report(payload):
    lines = ['# ORB, BOS and CHFJPY: July-August 2026 replay', '',
             'Each strategy runs on a separate account starting flat at $10,000 on July 1, with 1% balance risk, maximum 1 lot and no withdrawals. The main monthly rows carry capital and positions forward into August; profits are assigned by exit date. The end boundary is September 1 exclusive. These are offline backtests, not actual account fills.', '',
             'ORB exactly recovers the former deployed gold H1 signal from commit `665430a`, verified identical to the last pre-BOS version. Three-bar opening box from broker hour 1, structure filter on, volume filter off, box-boundary stop, structure target at least 1R away or 3R fallback, opposite-signal exits, no time exit. It is isolated from the USDJPY strategy that once shared its account. BOS uses the current retained GOLD M30 configuration with MA200.', '',
             '## Continuous $10,000 accounts', '',
             '| Strategy | July realized P/L | August realized P/L | Total | Ending balance | Trades | Wins / losses |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for name in ('ORB', 'BOS', 'CHFJPY'):
        r = next(x for x in payload['rows'] if x['strategy'] == name and x['window'] == 'Jul-Aug' and x['profile'] == 'base')
        months = [next(x for x in payload['months'] if x['strategy'] == name and x['profile'] == 'base' and x['month'] == m) for m in ('2026-07', '2026-08')]
        lines.append(f"| {name} | ${months[0]['net']:+,.2f} | ${months[1]['net']:+,.2f} | ${r['net']:+,.2f} | ${r['final_balance']:,.2f} | {r['trades']} | {r['wins']} / {r['losses']} |")
    lines += ['', '## Model differences and limits', '',
              '- ORB and BOS use the same archived gold execution convention: $0.30 price spread, no commission, swap or slippage, exact-price stop fills even across gaps, and closed-balance entry halts ($300 daily / $600 static). These are spread-adjusted results, not all-in execution estimates. Sizing uses signal-close stop distance before spread. Short spread is modeled on entry rather than through an ask series.',
              '- CHFJPY uses the existing guarded JPY research replay: 2.5-pip spread, $14/lot round-trip commission, 0.1-pip slippage per fill, historical USDJPY conversion, and floating-liquidation/headroom guards. No guards fired or entries were blocked in this particular two-month base run, but the engines still differ. Neither model includes swap or verifies broker-session mapping. This is not a controlled comparison of identical execution assumptions.',
              '- Both gold profiles preserve archived signal/engine quirks; no parameters were optimized on July-August. Current BOS parameters and choice of CHFJPY were already influenced by historical testing, so this is not an untouched out-of-sample validation.',
              '- Gold trade timestamps are candle opening labels: a signal at 05:00 executes at the completed H1 close, normally around 06:00. Intrabar SL/TP timestamps identify the bar containing the fill, not an exact fill time. CHFJPY ledger labels likewise are bar timestamps.',
              '- OHLC cannot establish order of intrabar touches; the gold simulator takes the stop first if both SL and TP occur within one candle. Period-end marks are artificial closes. Monthly realized P/L does not mark a held trade at month-end.', '',
              '## Wider-spread sensitivity', '',
              'Gold spread doubles to $0.60; CHFJPY doubles to 5 pips. Other assumptions remain unchanged.', '',
              '| Strategy | Base two-month P/L | Wide two-month P/L |', '|---|---:|---:|']
    for name in ('ORB', 'BOS', 'CHFJPY'):
        rs = [next(x for x in payload['rows'] if x['strategy'] == name and x['window'] == 'Jul-Aug' and x['profile'] == p) for p in ('base', 'wide')]
        lines.append(f"| {name} | ${rs[0]['net']:+,.2f} | ${rs[1]['net']:+,.2f} |")
    lines += ['', '## ORB: every trade in the continuous base run', '',
              '| Entry bar | Exit bar | Side | Lots | Entry | Exit | P/L | Exit reason |', '|---|---|---|---:|---:|---:|---:|---|']
    trades = pd.read_csv(OUT / 'ORB-base-Jul-Aug-trades.csv', parse_dates=['entry_time', 'exit_time'])
    for t in trades.itertuples():
        lines.append(f"| {t.entry_time:%Y-%m-%d %H:%M} | {t.exit_time:%Y-%m-%d %H:%M} | {t.side} | {t.lots:.2f} | {t.entry:.2f} | {t.exit:.2f} | ${t.profit:+.2f} | {t.reason} |")
    lines += ['', '`tp` = target, `sl` = stop, `signal` = opposite qualified signal. One trade entered July 31 and exited August 4; its full -$15.54 belongs to August realized P/L.', '',
              '## Independent fresh-month alternatives', '',
              'These reset to $10,000 and start flat at each month boundary. July ends by marking any remaining position. They must not be added to the continuous-account monthly rows above.', '',
              '| Strategy | Fresh July | Fresh August |', '|---|---:|---:|']
    for name in ('ORB', 'BOS', 'CHFJPY'):
        rs = [next(x for x in payload['rows'] if x['strategy'] == name and x['profile'] == 'base' and x['window'] == m) for m in ('July-fresh', 'August-fresh')]
        lines.append(f"| {name} | ${rs[0]['net']:+.2f} | ${rs[1]['net']:+.2f} |")
    lines += ['', '## Interpretation', '',
              'CHFJPY was the best of these three historical July-August replays under the stated models. ORB was nearly flat across both months and lost in August, so this sample does not establish ORB as a profitable replacement for recent BOS losses. BOS itself made money in July in this calendar test.', '',
              'The broader CHFJPY $10,000 account study had four profitable independent calendar years out of ten (2016-2025), six losing/headroom-limited years, and an arithmetic annual mean of +$157.05. Its recent +$5,294.44 year is therefore not enough to establish a dependable edge. Treat the switch as a demo hypothesis needing forward evidence, not a proven improvement. [Earlier account study](2026-09-13-jpy-account-comparison.md). Past performance cannot predict a strategy’s future performance. [SEC performance-claims bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-47).', '',
              'The earlier August CHFJPY figure +$523.00 came from a year-long account that entered August at $14,771.43. This report starts July at $10,000; its August figure is +$352.40. The differing capital paths explain why the amounts differ.', '',
              '## Reproduction and artifacts', '',
              'Run `.venv/Scripts/python -m research.orb_recent_recheck`. The script recovers archived source from git without restoring ORB in the live registry. It saves 18 trade ledgers, gold event logs, summary.csv, monthly.csv, source hashes and input audits in [the results folder](../logs/orb-recent-recheck-20260917/). Every run reconciles profits to its ending balance and every continuous monthly split to its run total. [Archive audit](2026-09-17-orb-archived-rules.md). No MT5 account connection, order or live configuration change is part of this replay.', '']
    (ROOT / 'docs/2026-09-17-orb-july-august-results.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    orb, orb_cfg, orb_hash = archived_orb()
    h1_path = ROOT / 'data/gold-research-h1-20260912.csv'
    m30_path = ROOT / 'data/xauusd-m30-volume-20260912.csv'
    h1, m30 = load_bars(h1_path), load_bars(m30_path)
    jpy_data, jpy_audit = frames()
    rows, months = [], []
    windows = [('Jul-Aug', START, END),
               ('July-fresh', START, pd.Timestamp('2026-08-01')),
               ('August-fresh', pd.Timestamp('2026-08-01'), END)]
    for label, start, end in windows:
        for name, df, cfg, strategy in [('ORB', h1, orb_cfg, orb), ('BOS', m30, GOLD, bos)]:
            for profile, spread in [('base', 3.), ('wide', 6.)]:
                adjusted = SimpleNamespace(**{**vars(cfg), 'spread_pips': spread}) if name == 'ORB' else replace(cfg, spread_pips=spread)
                summary, trades, events = gold_replay(df, adjusted, strategy, start, end)
                ledger = f'{name}-{profile}-{label}-trades.csv'
                trades.to_csv(OUT / ledger, index=False)
                pd.DataFrame(events).to_csv(OUT / f'{name}-{profile}-{label}-events.csv', index=False)
                rows.append(dict(strategy=name, profile=profile, window=label, ledger=ledger, **summary))
                if label == 'Jul-Aug':
                    for month in ('2026-07', '2026-08'):
                        selected = trades[trades.exit_time.dt.strftime('%Y-%m') == month]
                        months.append(dict(strategy=name, profile=profile, month=month,
                                           **{k: v for k, v in stats(selected).items() if k not in ('final_balance', 'closed_drawdown')}))
        for profile, spread in [('base', 2.5), ('wide', 5.)]:
            summary, trades = jpy_simulate(jpy_data['CHFJPY'], start, end,
                                           initial_balance=10000., spread_pips=spread, commission=14.)
            ledger = f'CHFJPY-{profile}-{label}-trades.csv'
            trades.to_csv(OUT / ledger, index=False)
            rows.append(dict(strategy='CHFJPY', profile=profile, window=label, ledger=ledger,
                             **stats(trades), research_guards=summary))
            if label == 'Jul-Aug':
                for month in ('2026-07', '2026-08'):
                    selected = trades[trades.exit_time.dt.strftime('%Y-%m') == month]
                    months.append(dict(strategy='CHFJPY', profile=profile, month=month,
                                       **{k: v for k, v in stats(selected).items() if k not in ('final_balance', 'closed_drawdown')}))
    for row in rows:
        if row['window'] == 'Jul-Aug':
            selected = [m for m in months if m['strategy'] == row['strategy'] and m['profile'] == row['profile']]
            assert abs(sum(m['net'] for m in selected) - row['net']) < 1e-6
            assert sum(m['trades'] for m in selected) == row['trades']
    payload = dict(archive_commit=COMMIT, orb_source_sha256=orb_hash, orb_config=vars(orb_cfg),
                   source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (h1_path, m30_path, Path(__file__), ROOT/'trader/sim.py',
                                            ROOT/'trader/engine.py', ROOT/'trader/strategies/bos.py')},
                   jpy_audit=jpy_audit, rows=rows, months=months)
    (OUT / 'results.json').write_text(json.dumps(payload, indent=2, default=str), encoding='utf-8')
    pd.DataFrame([{k: v for k, v in r.items() if k != 'research_guards'} for r in rows]).to_csv(OUT / 'summary.csv', index=False)
    pd.DataFrame(months).to_csv(OUT / 'monthly.csv', index=False)
    write_report(payload)
    print(pd.DataFrame(rows)[['strategy', 'profile', 'window', 'trades', 'wins', 'losses', 'net', 'final_balance']].to_string(index=False))
    print(pd.DataFrame(months).to_string(index=False))


if __name__ == '__main__':
    main()
