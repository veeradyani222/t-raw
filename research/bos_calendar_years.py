"""Calendar-year BOS results; full years and current YTD reported separately."""
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
from trader.strategies import bos
from trader.strategy import Setup, Signal
from research import bos_monthly_withdrawals as cashflow

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs/bos-calendar-years-20260913"
ASOF = pd.Timestamp("2026-09-12")


def main():
    logging.disable(logging.CRITICAL)
    OUT.mkdir(parents=True, exist_ok=True)
    data_path = ROOT/"data/bos-long-history-20260913.csv"
    data_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
    previous = json.loads((ROOT/"logs/bos-long-history-20260913/results.json").read_text())
    assert data_hash == previous["audit"]["merged_sha256"]
    df = pd.read_csv(data_path, parse_dates=["time"])
    periods = []
    for year in range(df.time.min().year, ASOF.year + 1):
        start = pd.Timestamp(year, 1, 1)
        if (df.time < start).sum() < GOLD.bos_lookback:
            continue
        end = min(pd.Timestamp(year + 1, 1, 1), ASOF)
        periods.append((start, end, end.month != 1 or end.day != 1))
    fast = make_bos_signal(df, swing_window=GOLD.bos_swing_window, cmf_n=GOLD.bos_cmf_n,
                           cmf_min=GOLD.bos_cmf_min, trend_ma=GOLD.bos_trend_ma,
                           lookback=GOLD.bos_lookback, tp_mode=GOLD.bos_tp_mode,
                           tp_r=GOLD.bos_tp_r, tp_min_r=GOLD.bos_tp_min_r)
    index = {t: i for i, t in enumerate(df.time)}
    checked = 0
    for start, _, _ in periods:
        first = int(df.time.searchsorted(start))
        for i in range(first, min(first + 8, len(df))):
            original = bos.compute_signal(df.iloc[i + 1 - GOLD.bos_lookback:i + 1], GOLD)
            slow = original if isinstance(original, Setup) else None
            f = fast(df, i)
            assert (slow is None) == (f is None)
            if slow is not None:
                assert slow.side == f.side
                np.testing.assert_allclose([slow.sl, slow.tp], [f.sl, f.tp], atol=1e-8, rtol=0)
            checked += 1

    def adapter(candles, cfg):
        s = fast(df, index[candles.time.iloc[-1]])
        return Setup(s.side, sl=s.sl, tp=s.tp) if s is not None else Signal.FLAT

    results = []
    with patch.object(bos, "compute_signal", adapter):
        # Recheck the known complete-year sequence after adding partial-window support.
        control = OUT/"control-september-year"
        control.mkdir(exist_ok=True)
        with patch.object(cashflow, "START", pd.Timestamp("2025-09-12")), patch.object(cashflow, "END", ASOF), patch.object(cashflow, "OUT", control):
            for policy in ("none", "positive_month"):
                _, trades = cashflow.replay(df, policy, quiet=True)
                saved = pd.read_csv(ROOT/f"logs/bos-monthly-withdrawals-20260912/{policy}-trades.csv")
                assert len(trades) == len(saved)
                for c in ("entry", "exit", "sl", "tp", "lots", "profit", "equity_after"):
                    np.testing.assert_allclose(trades[c], saved[c], atol=1e-8, rtol=0)
        print("Both original September-year controls reproduced; testing calendar years.", flush=True)
        for start, end, partial in periods:
            target = OUT/str(start.year)
            target.mkdir(exist_ok=True)
            with patch.object(cashflow, "START", start), patch.object(cashflow, "END", end), patch.object(cashflow, "OUT", target):
                for policy in ("none", "positive_month"):
                    result, _ = cashflow.replay(df, policy, quiet=True)
                    results.append(dict(year=start.year, start=str(start), end_exclusive=str(end),
                                        partial=partial, **result))
                    print(start.year, policy, "net", round(result["trading_pnl"], 2),
                          "cashout", round(result["withdrawals"], 2), "halt", result["blown_at"], flush=True)
    averages = {}
    for policy in ("none", "positive_month"):
        rows = [r for r in results if r["policy"] == policy and not r["partial"]]
        averages[policy] = dict(years=len(rows), mean_net=float(np.mean([r["trading_pnl"] for r in rows])),
                               mean_return_pct=float(np.mean([r["trading_pnl"] for r in rows])/100),
                               profitable_years=sum(r["trading_pnl"] > 0 for r in rows),
                               halted_years=sum(r["blown_at"] is not None for r in rows))
    config = {k: v for k, v in asdict(GOLD).items() if not k.startswith(("mt5_", "telegram_"))}
    payload = dict(config=config, data_sha256=data_hash, january_boundary_parity_checks=checked,
                   september_control_trade_parity=True, averages=averages, results=results,
                   source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (Path(__file__), ROOT/"research/bos_monthly_withdrawals.py",
                                            ROOT/"bos_backtest.py", ROOT/"run_live.py", ROOT/"trader/engine.py",
                                            ROOT/"trader/sim.py", ROOT/"trader/risk.py", ROOT/"trader/strategies/bos.py",
                                            ROOT/"trader/strategies/structure.py")})
    (OUT/"results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    pd.DataFrame([{k: v for k, v in r.items() if k != "monthly"} for r in results]).to_csv(OUT/"yearly-results.csv", index=False)
    lines = ["# BOS January–December yearly results — 13 September 2026", "",
             "Same current local main BOS M30 configuration: CMF20, MA200, 1% risk of remaining account balance, $300 daily and $600 static total loss guards, structure exits and opposite-signal closes. Each year starts a separate $10,000 account on January1, with preceding warmup. Full calendar years are 2019–2025. History starts in February2018, so 2018 is excluded. The 2026 row is January1 through September11, not a complete year and not annualized.", "",
             "The withdrawal column uses the requested rule: withdraw every positive calendar month's realized gain, including when balance is below $10,000. Losses carry forward. Positions carry over month ends. For the final partial September period, the remaining position is marked at the last available close and positive realized gain is hypothetically withdrawn at the cutoff. Net profit is cash withdrawn plus remaining account minus $10,000; it is not just the withdrawal amount.", "",
             "| Calendar year | Keep profits: net | Ending balance | Monthly withdrawals: cash out | Ending balance after withdrawals | Monthly withdrawals: net |",
             "|---|---:|---:|---:|---:|---:|"]
    for start, _, partial in periods:
        a = next(r for r in results if r["year"] == start.year and r["policy"] == "none")
        b = next(r for r in results if r["year"] == start.year and r["policy"] == "positive_month")
        label = str(start.year) + (" YTD through Sep11" if partial else " Jan–Dec")
        lines.append(f"| {label} | ${a['trading_pnl']:+.2f} | ${a['final_balance']:.2f} | ${b['withdrawals']:.2f} | ${b['final_balance']:.2f} | ${b['trading_pnl']:+.2f} |")
    lines += ["", "## Full-year averages (2019–2025 only)", "", "| Policy | Mean net/year | Mean return/year | Profitable years | Years internally halted |",
              "|---|---:|---:|---:|---:|"]
    for policy, a in averages.items():
        lines.append(f"| {policy} | ${a['mean_net']:+.2f} | {a['mean_return_pct']:+.2f}% | {a['profitable_years']}/{a['years']} | {a['halted_years']}/{a['years']} |")
    lines += ["", "These are arithmetic averages of independent yearly starts. Loss-limited years remain in the sample through December, including the zero-trade time after permanent halts. They are not a compounded return on a single surviving account. Different January/September start dates change capital, positions and risk-stop timing, so rebinning the older yearly totals would not reproduce these results.", "",
              "| Year | Halt date: keep profits | Halt date: withdrawals |", "|---|---|---|"]
    for start, _, partial in periods:
        rows = [r for r in results if r["year"] == start.year]
        lines.append(f"| {start.year} | {rows[0]['blown_at'] or 'No'} | {rows[1]['blown_at'] or 'No'} |")
    lines += ["", "## Verification and assumptions", "",
              f"The partial-period test verifies future candles are excluded and the final open position is marked before the cutoff payout. Both original September-year control scenarios reproduced every saved trade's price, size, profit and equity. January-boundary fast/production signal agreement was checked on {checked} bars. Every run reconciles trade P&L, monthly P&L, cash payouts and ending balances.", "",
              "Same simplified simulator as previous reports: fixed 3-pip spread, signal-close entries, stop-first OHLC ties, exact stop fills across gaps, closed-balance risk checks, no commission/swap/slippage/latency. Live checks floating equity. Static loss-floor and gross-withdrawal assumptions do not verify a firm's actual payout rules, splits, taxes or fees. Historical spans contain gaps and current settings were chosen using prior historical research. No live settings, trades or withdrawals were changed.", "",
              "Reproduce with `.venv\\Scripts\\python.exe -m research.bos_calendar_years`. Monthly and trade logs, CSV/JSON tables, data/source hashes and sanitized configuration: `logs/bos-calendar-years-20260913/`.", ""]
    report = ROOT/"docs/2026-09-13-bos-calendar-year-results.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(averages, indent=2), flush=True)
    print(report, flush=True)


if __name__ == "__main__":
    main()
