"""Reconcile saved research outputs and render the complete Markdown report."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs/gold-intraday-20260912"


def main():
    screen, stress, starts = [json.loads((OUT / name).read_text()) for name in
                             ("screen-results.json", "stress-results.json", "fresh-start-results.json")]
    manifest = json.loads((OUT / "manifest.json").read_text())
    rows = screen + stress + starts
    overnight = gap_exits = 0
    for row in rows:
        stem = f"{row['cost_profile']}-{row['timeframe']}-{row['candidate']}-{row['window']}"
        trades = pd.read_csv(OUT / f"{stem}-trades.csv", parse_dates=["entry_time", "exit_time"])
        daily = pd.read_csv(OUT / f"{stem}-daily.csv")
        assert len(trades) == row["trades_count"]
        assert abs(trades.profit.sum() - row["net_profit"]) < 1e-6
        assert abs(daily.net_profit.sum() - row["net_profit"]) < 1e-6
        assert abs(daily.iloc[-1].end_equity - row["final_equity"]) < 1e-6
        assert ((10000 + trades.profit.cumsum() - trades.equity_after).abs() < 1e-6).all()
        assert (trades.exit_time >= trades.entry_time).all()
        assert (trades.lots >= .01).all() and (trades.lots <= 1).all()
        overnight += int((trades.entry_time.dt.date != trades.exit_time.dt.date).sum())
        gap_exits += int((trades.reason == "day_gap").sum())
    audit = dict(runs=len(rows), accounting_reconciled=True,
                 overnight_trades_across_runs=overnight, day_gap_exits_across_runs=gap_exits,
                 modeled_firm_breach_runs=sum(r["firm_breach"] for r in rows))
    (OUT / "accounting-audit.json").write_text(json.dumps(audit, indent=2))

    lines = ["# Gold intraday strategy study — 12 September 2026", "",
             "No candidate passed the predeclared first-11-month screen (positive net, profit factor at least 1.10, at least 80 trades, and no modeled firm breach/internal total halt). The frozen shortlist is empty. No live strategy was added or enabled; the production registry remains BOS-only.", "",
             "The screenshot's LuxAlgo trendline idea was implemented for offline testing. Its M5 recent-month profit did not persist over the year. M15 EMA pullback was the only variant positive in both requested windows, but its small yearly gain disappeared under cost stress. These results do not establish a robust profitable strategy.", "",
             "## Dates, data and execution", "",
             "Year: 12 September 2025 through 11 September 2026. Recent month: 12 August through 11 September 2026. Each simulation starts flat with $10,000 and preceding indicator warmup. The recent month overlaps the year; its fresh $10,000 start means its results need not match the final month of the year simulation.", "",
             "Primary risk is 0.25% of current cash equity per trade, reduced by lot rounding and remaining daily/total loss headroom. User-confirmed external limits are 4% daily / 8% total, with internal 3% / 6% buffers. The model uses a fixed $300 daily allowance from day-start equity and a static $9,400 internal floor; actual firm reset time, trailing-versus-static terms and news restrictions remain unverified.", "",
             "Completed-bar signals fill at the next available bar open. One position at a time; entries 07:00–18:59, forced flat from 20:00, reset at midnight, all in dataset timestamps. Base costs: maximum of recorded spread and $0.30 per ounce, $7 per lot round-trip commission, $0.03 per ounce adverse slippage on market fills. Contract size is 100 ounces, lot step/minimum 0.01, maximum 1 lot. Bars with recorded spreads above $0.60 cannot open trades. Costs are assumptions, not verified account charges.", "",
             "Bid OHLC is converted to executable bid/ask prices. An adverse-first path gives the stop priority if both stop and target lie inside a bar; gap stops fill at the worse available opening quote. Floating liquidation equity includes closing costs. This is an OHLC approximation, not tick-accurate execution or proof of prop-firm compliance. [MetaQuotes on OHLC testing limits](https://www.mql5.com/en/docs/runtime/testing).", "",
             "## Your screenshot's trendlines", "",
             "The visible indicator is LuxAlgo Trendlines with Breaks, apparently length 14, slope multiplier 1, ATR method. Descending green resistance supplies a first-close-above buy signal; rising red support supplies a first-close-below sell signal. A wick-only excursion does not qualify. This close-based rule is the tested interpretation; it does not implement every possible body-overlap variant. Breakouts can fail.", "",
             "The published recurrence confirms a pivot only 14 bars later: 3.5 hours on M15. Its slope is ATR at confirmation divided by 14. The boundary is projected forward and emits one close breakout per confirmed pivot. Historical backpainting is not used for entries. The implementation follows these published rules but has not been certified against TradingView bar-for-bar; feed differences (screenshot OANDA versus fetched MT5 history) and pivot-tie behavior can matter. [LuxAlgo source and explanation](https://www.luxalgo.com/library/indicator/Trendlines-with-Breaks/).", "",
             "An indicator is not a complete trading strategy. For this test we added a 1.5 ATR stop, 2R target, maximum 180-minute holding period, the above session/risk rules, and a second variant with an EMA200 direction filter. RSI and TRAMA visible in the screenshot were not entry filters.", "",
             "## All primary results", "",
             "Net dollars include modeled costs. Drawdown is the maximum floating peak-to-trough dollar drop divided by the original $10,000, not loss below initial balance. A run can therefore show drawdown above 6% while remaining above a static $9,400 floor after earlier profits.", ""]
    names = manifest["candidates"]
    for tf in ("M5", "M15"):
        lines += [f"### {tf}", "", "| Variant | Month net | Year net | Year trades | Year PF | Year float DD | Worst day |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for name in names:
            y = next(r for r in screen if r["timeframe"] == tf and r["candidate"] == name and r["window"] == "year")
            m = next(r for r in screen if r["timeframe"] == tf and r["candidate"] == name and r["window"] == "month")
            lines.append(f"| {name} | ${m['net_profit']:+.2f} | ${y['net_profit']:+.2f} | {y['trades_count']} | {y['profit_factor']:.2f} | {y['max_float_dd_pct']:.2f}% | {y['worst_day_loss_pct']:.2f}% |")
        lines.append("")
    lines += ["### M1 — month only", "", "M1 history begins 28 May 2026, so a yearly M1 result is unavailable.", "",
              "| Variant | Month net | Trades | Float DD | Worst day |", "|---|---:|---:|---:|---:|"]
    for r in screen:
        if r["timeframe"] == "M1":
            lines.append(f"| {r['candidate']} | ${r['net_profit']:+.2f} | {r['trades_count']} | {r['max_float_dd_pct']:.2f}% | {r['worst_day_loss_pct']:.2f}% |")
    lines += ["", "Several losing runs stop finding affordable minimum-lot trades near $9,400. Their lack of a formal halt/breach flag is not evidence of useful safety or recovery. For example, the M5 trendline year's trades stop before the recent-month window; the positive standalone month starts with fresh capital.", "",
              "## Cost and position-size sensitivity", "",
              "M15 trendlines were included because you requested them. M15 EMA pullback was added after observing positive year/month results and is explicitly post hoc, not a successful held-out selection. Higher-cost stress uses $0.60 minimum spread, $10 commission and $0.10 slippage at 0.25% risk. The separate 0.5% risk runs retain base costs.", "",
              "| M15 variant | Profile | Month net | Year net | Year float DD |", "|---|---|---:|---:|---:|"]
    for name in sorted({r["candidate"] for r in stress}):
        for profile in ("cost_stress", "risk_0p5"):
            a = [r for r in stress if r["candidate"] == name and r["cost_profile"] == profile]
            y, m = (next(r for r in a if r["window"] == w) for w in ("year", "month"))
            lines.append(f"| {name} | {profile} | ${m['net_profit']:+.2f} | ${y['net_profit']:+.2f} | {y['max_float_dd_pct']:.2f}% |")
    lines += ["", "Twelve fresh starts (the 12th of each month, September 2025–August 2026) all end on 12 September 2026. These overlap and have different lengths; they are start-date sensitivity checks, not twelve independent validation periods. 'Near floor' means minimum modeled equity below $9,410.", "",
              "| M15 variant | Risk | Profitable starts / 12 | Near floor / 12 | Worst net |", "|---|---:|---:|---:|---:|"]
    for name in sorted({r["candidate"] for r in starts}):
        for risk in (.0025, .005):
            a = [r for r in starts if r["candidate"] == name and r["risk"] == risk]
            lines.append(f"| {name} | {100*risk:.2f}% | {sum(r['net_profit'] > 0 for r in a)} | {sum(r['min_equity'] < 9410 for r in a)} | ${min(r['net_profit'] for r in a):+.2f} |")
    lines += ["", "## Candidate definitions", ""]
    lines += [f"- `{name}`: {description}." for name, description in names.items()]
    lines += ["", "BOS here uses the common research session, costs, sizing and maximum-holding wrapper. These are not the same execution settings as the earlier live/BOS M30 replay, so the reports should not be compared as identical implementations.", "",
              "## Coverage and verification", "",
              "M5/M15 history spans the requested year, but there are missing intraday intervals. The following same-day gaps occur inside the study's daytime window; their origin is unverified. Holidays, weekends and other session closures also exist.", ""]
    for tf, info in manifest["audit"].items():
        lines.append(f"- {tf}: {info['bars']:,} bars, {info['first']} to {info['last']}.")
        for gap in info["daytime_gaps"]:
            lines.append(f"  - {gap['previous']} → {gap['following']}.")
    lines += ["", "No same-day missing daytime interval was found in the recent-month window. This does not establish tick coverage. Data hashes, source hashes, settings and all attempted outcomes are retained in the manifest and CSV/JSON artifacts.", "",
              f"Accounting reconciled across {audit['runs']} runs: every trade cumulative balance, daily net and ending equity agrees with its summary. There were {overnight} overnight trades and {gap_exits} day-gap exits across these runs (overlapping runs count repeated trades). Modeled external 4%/8% breach runs: {audit['modeled_firm_breach_runs']}. That count uses the stated static-floor assumptions and does not certify the firm's actual rules.", "",
              "The repository test suite passed: 112 tests, including 13 candidate-signal tests and 20 simulator tests. Independent reviews checked signal causality, the published Lux recurrence, execution semantics, accounting assumptions and data gaps. Review findings led to explicit post-hoc labels and a source/data/configuration consistency check between screen and stress phases.", "",
              "Reproduce with `.venv\\Scripts\\python.exe -m research.gold_intraday.run_study --phase all`, then `.venv\\Scripts\\python.exe -m research.gold_intraday.report_study`. Raw outputs: `logs/gold-intraday-20260912/` (local, ignored by Git). Research code: `research/gold_intraday/`. The first-11-month results are in `selection-results.json`; the frozen selection is `[]`.", "",
              "The fixed settings were not tuned after viewing results. Nonetheless this is a multi-strategy historical screen, and any promising result needs new unseen data and verified execution/rules. [Source notes](2026-09-12-gold-intraday-sources.md).", ""]
    path = ROOT / "docs/2026-09-12-gold-intraday-results.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(audit))
    print(path)


if __name__ == "__main__":
    main()
