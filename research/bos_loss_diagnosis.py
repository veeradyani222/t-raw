"""Reproduce the saved BOS live-configuration replay and audit monthly losses."""
from dataclasses import asdict
import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from run_live import GOLD
from trader.engine import on_bar
from trader.risk import RiskGuard
from trader.sim import SimBroker

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs/bos-monthly-diagnosis-20260912"
START = pd.Timestamp("2025-09-12")
END = pd.Timestamp("2026-09-12")


def stats(trades):
    p = trades.profit
    wins, losses = p[p > 0], p[p < 0]
    streak = longest = 0
    for profit in p:
        streak = streak + 1 if profit < 0 else 0
        longest = max(longest, streak)
    return dict(trades=len(p), wins=len(wins), losses=len(losses), net=float(p.sum()),
                win_rate=100 * len(wins)/len(p) if len(p) else 0,
                gross_wins=float(wins.sum()), gross_losses=float(losses.sum()),
                avg_win=float(wins.mean()) if len(wins) else 0,
                avg_loss=float(losses.mean()) if len(losses) else 0,
                profit_factor=float(wins.sum()/-losses.sum()) if len(losses) else None,
                longest_loss_streak=longest)


def replay(df, start, end, label):
    broker = SimBroker(df, GOLD, 10000)
    guard = RiskGuard(GOLD.max_open_positions, GOLD.daily_loss_halt,
                      GOLD.max_drawdown_halt, GOLD.loss_baseline, GOLD.total_loss_halt)
    indices = np.flatnonzero(((df.time >= start) & (df.time < end)).to_numpy())
    blown_at = None
    for i in indices:
        broker.cursor = int(i)
        broker.check_stops()
        event = on_bar(broker, guard, GOLD)
        if guard.blown and blown_at is None:
            blown_at = df.time.iloc[i]
        if event is not None:
            if event["kind"] == "open":
                broker.attach_meta(event["ticket"], event.get("meta", {}))
            else:
                broker.events.append(event)
    for pos in list(broker.positions):
        broker._settle(pos, df.close.iloc[indices[-1]], "end")
    trades = pd.DataFrame(broker.trades)
    assert abs(10000 + trades.profit.sum() - broker.equity()) < 1e-6
    assert ((10000 + trades.profit.cumsum() - trades.equity_after).abs() < 1e-6).all()
    trades.to_csv(OUT / f"{label}-trades.csv", index=False)
    pd.DataFrame(broker.events).to_csv(OUT / f"{label}-events.csv", index=False)
    s = dict(start=str(start), end_exclusive=str(end), **stats(trades),
             final_equity=broker.equity(), blown_at=blown_at)
    print(label, s["trades"], round(s["net"], 2), "halt", blown_at, flush=True)
    return s, trades


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    path = ROOT / "data/xauusd-m30-volume-20260912.csv"
    df = pd.read_csv(path, parse_dates=["time"])
    assert df.time.is_monotonic_increasing and not df.time.duplicated().any()
    year, annual_trades = replay(df, START, END, "year")
    fresh, continuous = [], []
    for i in range(12):
        start = START + pd.DateOffset(months=i)
        end = START + pd.DateOffset(months=i+1)
        summary, trades = replay(df, start, end, f"fresh-{start:%Y%m%d}")
        fresh.append(summary)
        in_period = annual_trades[(annual_trades.time >= start) & (annual_trades.time < end)]
        continuous.append(dict(start=str(start), end_exclusive=str(end), **stats(in_period)))
    for tag, actual in (("2025-09-12", year), ("2026-08-12", fresh[-1])):
        saved = json.loads((ROOT / f"logs/m30-close-baseline-{tag}-summary.json").read_text())
        assert actual["trades"] == saved["trades"] and actual["wins"] == saved["wins"]
        assert abs(actual["net"] - saved["net"]) < 1e-6
    month_trades = pd.read_csv(OUT / "fresh-20260812-trades.csv", parse_dates=["time", "entry_time"])
    # Rank daily-shifted trailing calendar-month realized P&L on the same account.
    rolling = []
    for end in pd.date_range(START + pd.DateOffset(months=1), END, freq="D"):
        start = end - pd.DateOffset(months=1)
        if start < START:
            continue
        t = annual_trades[(annual_trades.time >= start) & (annual_trades.time < end)]
        before = annual_trades[annual_trades.time < start]
        balance = 10000 + before.profit.sum()
        rolling.append(dict(start=str(start), end_exclusive=str(end), net=float(t.profit.sum()),
                            starting_balance=float(balance), return_pct=float(100*t.profit.sum()/balance)))
    worst = min(rolling, key=lambda r: r["return_pct"])
    # Verify the rectangular-body criterion at every entry, using stored break levels.
    indexed = df.set_index("time")
    for _, t in annual_trades.iterrows():
        bar = indexed.loc[t.entry_time]
        assert (bar.close > t.level and bar.close > bar.open) if t.side == "long" else (bar.close < t.level and bar.close < bar.open)
    reasons = month_trades.groupby("reason").profit.agg(["count", "sum"]).reset_index().to_dict("records")
    sides = month_trades.groupby("side").profit.agg(["count", "sum"]).reset_index().to_dict("records")
    cfg = {k: v for k, v in asdict(GOLD).items() if not k.startswith(("mt5_", "telegram_"))}
    output = dict(config=cfg, data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [Path(__file__), ROOT/"run_live.py", ROOT/"trader/sim.py",
                                           ROOT/"trader/engine.py", ROOT/"trader/risk.py",
                                           ROOT/"trader/strategies/bos.py", ROOT/"trader/strategies/structure.py"]},
                  year=year, fresh_months=fresh, continuous_months=continuous, worst_rolling_month=worst,
                  latest_reasons=reasons, latest_sides=sides,
                  saved_baselines_reproduced=True, all_annual_entries_body_confirmed=True)
    (OUT / "diagnosis.json").write_text(json.dumps(output, indent=2, default=str))
    pd.DataFrame(fresh).to_csv(OUT/"fresh-months.csv", index=False)
    pd.DataFrame(continuous).to_csv(OUT/"continuous-months.csv", index=False)
    pd.DataFrame(rolling).to_csv(OUT/"rolling-months.csv", index=False)
    latest = fresh[-1]
    lines = ["# BOS monthly loss diagnosis — 12 September 2026", "",
             "This reproduces the saved local live-configuration BOS M30 backtest, not executed live-account P&L. Remote deployed code and actual deals have not been verified. Both saved baselines reproduce to numerical tolerance: 28 trades / -$466.60 for 12 August–11 September 2026, and 266 trades / +$3,104.21 for 12 September 2025–11 September 2026.", "",
             "Configuration: run_live.GOLD, 1% equity risk, MA200, CMF20 sign, swing window2, 2000-bar context, structure stop/target, minimum1R target, 3R fallback, one position, opposite-signal exits, $300 daily / $600 static total guard. All prior context is available before each start; each fresh run starts flat with $10,000. No session filter or three-hour holding cap was added.", "",
             "## Comparable months", "",
             "Each period runs from the 12th through the following 11th. Fresh results reset to $10,000 and start flat, directly matching the recent-month test. The continuous column groups the one-year account's realized exits and carries capital and positions forward. These different capital/exposure histories cannot be mixed.", "",
             "| Period start | Fresh net | Fresh trades | Win rate | Fresh permanent halt | Continuous net |",
             "|---|---:|---:|---:|---|---:|"]
    for f, c in zip(fresh, continuous):
        lines.append(f"| {f['start'][:10]} | ${f['net']:+.2f} | {f['trades']} | {f['win_rate']:.1f}% | {f['blown_at'] or 'No'} | ${c['net']:+.2f} |")
    lines += ["", f"Of the preceding 11 fresh monthly windows, {sum(r['net'] <= latest['net'] for r in fresh[:-1])} lost at least as much as the latest -$466.60. The worst fresh window started {min(fresh, key=lambda r:r['net'])['start'][:10]}.", "",
              f"Worst daily-shifted trailing calendar month on the continuous account: {worst['start'][:10]} to {worst['end_exclusive'][:10]} (exclusive), ${worst['net']:+.2f}, {worst['return_pct']:+.2f}% of its opening closed balance. These overlapping windows are descriptive, not independent trials or new monthly-reset simulations.", "",
              "## What drove the recent loss", "",
              f"Recent month: {latest['wins']} wins / {latest['losses']} losses, {latest['win_rate']:.2f}% win rate versus {year['win_rate']:.2f}% over the year. Gross winners ${latest['gross_wins']:.2f}; gross losses ${latest['gross_losses']:.2f}; net ${latest['net']:+.2f}. Average winner ${latest['avg_win']:.2f}, average loser ${latest['avg_loss']:.2f}; profit factor {latest['profit_factor']:.3f}. Longest consecutive losing-trade run: {latest['longest_loss_streak']}.", "",
              "| Exit reason | Trades | Net |", "|---|---:|---:|"]
    lines += [f"| {r['reason']} | {r['count']} | ${r['sum']:+.2f} |" for r in reasons]
    lines += ["", "| Side | Trades | Net |", "|---|---:|---:|"]
    lines += [f"| {r['side']} | {r['count']} | ${r['sum']:+.2f} |" for r in sides]
    lines += ["", "The losses predominantly came from qualifying breakouts subsequently hitting their structural stops. Both directions lost; long trades contributed more net loss. The body-close rule passed on every entry in the one-year replay, so wick-only entries do not explain this backtest loss. The MA200 and CMF-sign filters do not prevent all failed breakouts. This does not establish a particular macroeconomic or news cause.", "",
              "Structure exits are not universally 3R targets: 3R is only the fallback. In the latest month, 23 trades used structure targets and five used the fallback. The realized win rate and payouts together were insufficient to cover the losers. The last losing trade is an artificial end-of-test mark, not necessarily an actual live exit.", "",
              "Changing filters to remove these particular past losers would be retrospective fitting. This diagnosis establishes the failure pattern, not a verified repair or a promise of positive future returns. Current settings were selected after earlier historical testing; the one-year replay is not a fully unseen forward test.", "",
              "## Limits and artifacts", "",
              "SimBroker matches the production decision engine but simplifies execution: signal-bar close plus fixed spread, stop-first ties, exact stop fills even on gaps, no commission/swap/slippage/latency, and risk guards based on closed balance. Actual live risk checks use floating equity. The earlier intraday research BOS numbers used different hours, costs and holding limits and are not this model. No live configuration was changed.", "",
              "Data ends 11 September 2026 at 21:30 in dataset timestamps, matching the original saved replay. Recorded bars include gaps; broker feed and execution parity remain unverified. Trade accounting, saved-baseline reproduction and every entry's body-cross condition were checked. Raw trades, event logs, monthly tables, rolling windows, source/data hashes and sanitized settings are in `logs/bos-monthly-diagnosis-20260912/`. Reproduce with `.venv\\Scripts\\python.exe -m research.bos_loss_diagnosis`.", ""]
    report = ROOT/"docs/2026-09-12-bos-monthly-loss-diagnosis.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(report, flush=True)


if __name__ == "__main__":
    main()
