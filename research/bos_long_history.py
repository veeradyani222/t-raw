"""Fixed BOS settings over every complete available September-to-September year."""
from dataclasses import asdict
import hashlib
import json
import logging
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from bos_backtest import make_bos_signal
from run_live import GOLD
from trader.engine import on_bar
from trader.risk import RiskGuard
from trader.sim import SimBroker
from trader.strategies import bos
from trader.strategy import Setup, Signal
from research import bos_monthly_withdrawals as cashflow

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs/bos-long-history-20260913"
END = pd.Timestamp("2026-09-12")


def build_history():
    # The recent snapshot is the exact source of the previously reproduced year.
    paths = [ROOT/"data/xauusd-m30.csv", ROOT/"data/xauusd-m30-volume-20260912.csv"]
    frames = [pd.read_csv(p, parse_dates=["time"]) for p in paths]
    cols = ["time", "open", "high", "low", "close", "tick_volume"]
    merged = pd.concat([f[cols] for f in frames]).drop_duplicates("time", keep="last").sort_values("time").reset_index(drop=True)
    merged = merged[merged.time < END].reset_index(drop=True)
    assert merged.time.is_monotonic_increasing and not merged.time.duplicated().any()
    assert np.isfinite(merged[cols[1:]].to_numpy()).all()
    assert (merged.tick_volume > 0).all()
    assert (merged.high >= merged[["open", "close", "low"]].max(axis=1)).all()
    assert (merged.low <= merged[["open", "close"]].min(axis=1)).all()
    path = ROOT/"data/bos-long-history-20260913.csv"
    merged.to_csv(path, index=False)
    overlap = frames[0].merge(frames[1], on="time", suffixes=("_old", "_new"))
    mismatches = {c: int(((overlap[c+"_old"] - overlap[c+"_new"]).abs() > 1e-8).sum()) for c in cols[1:]}
    probes = []
    for year in (2016, 2017, 2018):
        p = ROOT/f"data/bos-history-probe-{year}-20260913.csv"
        if p.exists():
            f = pd.read_csv(p, parse_dates=["time"])
            valid = f[(f.time >= pd.Timestamp(year, 1, 1)) & (f.time < pd.Timestamp(year+1, 1, 1))]
            probes.append(dict(requested_year=year, returned_bars=len(f), in_requested_year=len(valid),
                               first_returned=str(f.time.min()), last_returned=str(f.time.max())))
    return merged, dict(sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                        merged_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        bars=len(merged), first=str(merged.time.min()), last=str(merged.time.max()),
                        overlap_differences=mismatches, older_history_probes=probes)


def validate_fast_path(df, fn, year_starts):
    # Stratified old/recent bars plus actual signal bars, deterministic sampling.
    signal_indices = [i for i in range(2000, len(df)) if fn(df, i) is not None]
    rng = np.random.default_rng(20260913)
    selected = set(rng.choice(np.arange(2000, len(df)), 160, replace=False).tolist())
    selected.update(rng.choice(signal_indices, min(160, len(signal_indices)), replace=False).tolist())
    for start in year_starts:
        i = int(df.time.searchsorted(start))
        selected.update(range(i, min(i + 8, len(df))))
    for i in sorted(selected):
        original = bos.compute_signal(df.iloc[max(0, i+1-GOLD.bos_lookback):i+1], GOLD)
        slow = original if isinstance(original, Setup) else None
        fast = fn(df, i)
        assert (slow is None) == (fast is None), (i, df.time.iloc[i])
        if slow is not None:
            assert slow.side == fast.side
            np.testing.assert_allclose([slow.sl, slow.tp], [fast.sl, fast.tp], atol=1e-8, rtol=0)
    return len(selected)


def continuous_account(df, start):
    broker = SimBroker(df, GOLD, 10000.)
    guard = RiskGuard(GOLD.max_open_positions, GOLD.daily_loss_halt,
                      GOLD.max_drawdown_halt, GOLD.loss_baseline, GOLD.total_loss_halt)
    blown_at = None
    for i in np.flatnonzero(((df.time >= start) & (df.time < END)).to_numpy()):
        broker.cursor = int(i)
        broker.check_stops()
        event = on_bar(broker, guard, GOLD)
        if guard.blown and blown_at is None:
            blown_at = df.time.iloc[i]
        if event is not None and event["kind"] == "open":
            broker.attach_meta(event["ticket"], event.get("meta", {}))
    for pos in list(broker.positions):
        broker._settle(pos, df.close.iloc[-1], "end")
    trades = pd.DataFrame(broker.trades)
    assert abs(10000 + trades.profit.sum() - broker.equity()) < 1e-6
    trades.to_csv(OUT/"one-continuous-account-trades.csv", index=False)
    return dict(start=str(start), final_balance=broker.equity(), net=float(trades.profit.sum()),
                trades=len(trades), blown_at=blown_at)


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    df, audit = build_history()
    starts = [END - pd.DateOffset(years=i) for i in range(10, 0, -1)]
    starts = [s for s in starts if int((df.time < s).sum()) >= GOLD.bos_lookback]
    fn = make_bos_signal(df, swing_window=GOLD.bos_swing_window, cmf_n=GOLD.bos_cmf_n,
                         cmf_min=GOLD.bos_cmf_min, trend_ma=GOLD.bos_trend_ma,
                         lookback=GOLD.bos_lookback, tp_mode=GOLD.bos_tp_mode,
                         tp_r=GOLD.bos_tp_r, tp_min_r=GOLD.bos_tp_min_r)
    checks = validate_fast_path(df, fn, starts)
    print("History", audit["first"], "to", audit["last"], "years", len(starts),
          "production signal parity checks", checks, flush=True)
    index = {timestamp: i for i, timestamp in enumerate(df.time)}

    def adapter(candles, cfg):
        signal = fn(df, index[candles.time.iloc[-1]])
        return Setup(signal.side, sl=signal.sl, tp=signal.tp) if signal is not None else Signal.FLAT

    results = []
    with patch.object(bos, "compute_signal", adapter):
        for start in starts:
            end = start + pd.DateOffset(years=1)
            target = OUT/f"year-{start:%Y%m%d}"
            target.mkdir(exist_ok=True)
            with patch.object(cashflow, "START", start), patch.object(cashflow, "END", end), patch.object(cashflow, "OUT", target):
                for policy in ("none", "positive_month"):
                    result, trades = cashflow.replay(df, policy)
                    if start == pd.Timestamp("2025-09-12"):
                        path = ROOT/f"logs/bos-monthly-withdrawals-20260912/{policy}-trades.csv"
                        saved = pd.read_csv(path)
                        assert len(trades) == len(saved)
                        for c in ("entry", "exit", "lots", "sl", "tp", "profit", "equity_after"):
                            np.testing.assert_allclose(trades[c], saved[c], atol=1e-8, rtol=0)
                    results.append(dict(start=str(start), end_exclusive=str(end), **result))
        carried = continuous_account(df, starts[0])
    averages = {}
    for policy in ("none", "positive_month"):
        r = [x for x in results if x["policy"] == policy]
        vals = [x["trading_pnl"] for x in r]
        averages[policy] = dict(years=len(r), profitable_years=sum(v > 0 for v in vals),
                               mean_net=float(np.mean(vals)), median_net=float(np.median(vals)),
                               mean_return_pct=float(np.mean(vals)/100), sum_independent_nets=float(sum(vals)),
                               mean_withdrawals=float(np.mean([x["withdrawals"] for x in r])),
                               halted_years=sum(x["blown_at"] is not None for x in r))
    config = {k: v for k, v in asdict(GOLD).items() if not k.startswith(("mt5_", "telegram_"))}
    payload = dict(audit=audit, config=config, signal_parity_bars=checks,
                   recent_year_trade_parity=True, averages=averages, continuous_account=carried,
                   source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (Path(__file__), ROOT/"research/bos_monthly_withdrawals.py",
                                            ROOT/"bos_backtest.py", ROOT/"trader/engine.py", ROOT/"trader/sim.py",
                                            ROOT/"trader/risk.py", ROOT/"trader/strategies/bos.py",
                                            ROOT/"trader/strategies/structure.py", ROOT/"run_live.py")},
                   results=results)
    (OUT/"results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    pd.DataFrame([{k: v for k, v in r.items() if k != "monthly"} for r in results]).to_csv(OUT/"yearly-results.csv", index=False)
    lines = ["# BOS yearly results over available history — 13 September 2026", "",
             f"Cached XAUUSD M30 history spans {audit['first']} through {audit['last']}: {audit['bars']:,} bars. There are {len(starts)} complete September-to-September years with at least 2,000 preceding warmup bars. A full ten-year test is unavailable. MT5 requests for 2016 and 2017 returned a single out-of-range 2018 bar, which was rejected as evidence of coverage. Existing cached early-2018 data was retained. The recent snapshot supersedes overlapping cached bars; overlap differences are logged in the manifest.", "",
             "Every row is a new hypothetical $10,000 account with the same current local live BOS M30 settings, 1% risk, MA200, CMF20, 2-bar fractal swings, 2,000-bar context, structure exits, minimum1R / fallback3R, opposite-signal exits, $300 daily and $600 static total guard. No settings are tuned for individual years. Monthly cash-flow periods start on the 12th. Losing accounts remain stopped until that yearly run ends; the following row starts a separate account, not a reset of the same account.", "",
             "The monthly-withdrawal variant pays out every positive month's realized gain even when the account is below $10,000, as requested. Losses remain in the account. Its net result is withdrawals plus ending account balance minus $10,000. Gross cash withdrawn alone is not net profit. The fixed $9,400 floor is a simulation assumption; actual firm's payout eligibility, split, fees and post-payout rules are unverified.", "",
             "## Yearly comparison", "",
             "Each period starts September 12 and ends September 11 of the following year. All net figures include losing years and the effect of risk stops.", "",
             "| Year | Keep profits: net | Keep profits: ending balance | Monthly withdrawals: cash out | Monthly withdrawals: ending balance | Monthly withdrawals: net |",
             "|---|---:|---:|---:|---:|---:|"]
    for start in starts:
        a = next(r for r in results if r["start"] == str(start) and r["policy"] == "none")
        b = next(r for r in results if r["start"] == str(start) and r["policy"] == "positive_month")
        lines.append(f"| {start.year}–{start.year+1} | ${a['trading_pnl']:+.2f} | ${a['final_balance']:.2f} | ${b['withdrawals']:.2f} | ${b['final_balance']:.2f} | ${b['trading_pnl']:+.2f} |")
    lines += ["", "## Averages across independent yearly starts", "",
              "| Policy | Profitable years | Mean annual net | Mean annual return | Median annual net | Years halted | Mean cash withdrawn |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for policy, a in averages.items():
        lines.append(f"| {policy} | {a['profitable_years']}/{a['years']} | ${a['mean_net']:+.2f} | {a['mean_return_pct']:+.2f}% | ${a['median_net']:+.2f} | {a['halted_years']}/{a['years']} | ${a['mean_withdrawals']:.2f} |")
    lines += ["", "These are arithmetic averages of separate $10,000 yearly trials, not a compounded multi-year return or a prediction of annual income. Halted years remain in the denominator; their zero-trade remainder is not omitted. Simulated losses can exceed $600 because the guard blocks new entries after the threshold is breached rather than guaranteeing an exit at exactly $9,400.", "",
              f"One account carried from {carried['start'][:10]} through the entire history, with no withdrawals or yearly resets, ended at ${carried['final_balance']:.2f}; net ${carried['net']:+.2f}, {carried['trades']} trades. Permanent halt: {carried['blown_at']}. Thus independent yearly results must not be presented as what that one account would have earned.", "",
              "## Halt dates", "", "| Year start | Keeping profits | Monthly withdrawals |", "|---|---|---|"]
    for start in starts:
        r = [r for r in results if r["start"] == str(start)]
        lines.append(f"| {start:%Y-%m-%d} | {r[0]['blown_at'] or 'No'} | {r[1]['blown_at'] or 'No'} |")
    lines += ["", "## Verification and limits", "",
              f"The existing fast BOS signal implementation matched the original production function on {checks} deterministic checks spread across years, including actual signal bars and year boundaries. It ran through the same production decision engine and cash-flow simulator. Both recent-year variants reproduced every saved trade's entry, exit, size, stop, target, profit and post-trade equity. Trade P&L, monthly P&L, withdrawals and ending balances reconciled in all yearly runs.", "",
              "The execution model remains deliberately simplified: fixed 3-pip spread, signal-close entry, stop-first OHLC ties, exact stop fills across gaps, closed-balance guards, and no commission, swap, slippage or latency. Live risk uses floating equity. History spans the stated dates but is not certified gap-free or tick-complete. The current strategy was selected using historical research; this is retrospective application of current settings, not eight years of live or fully unseen performance. No live strategy, risk setting, order or payout changed.", "",
              "Reproduce with `.venv\\Scripts\\python.exe -m research.bos_long_history`. Data/provenance, complete monthly and trade logs, yearly results and averages are in `logs/bos-long-history-20260913/`.", ""]
    report = ROOT/"docs/2026-09-13-bos-yearly-results.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(averages, indent=2), flush=True)
    print(report, flush=True)


if __name__ == "__main__":
    main()
