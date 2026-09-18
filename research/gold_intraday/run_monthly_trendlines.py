"""Offline fixed trendline study at 1% risk; no live configuration changes.

Run: python -m research.gold_intraday.run_monthly_trendlines
"""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import pandas as pd

from .candidates import build_signals
from .simulator import SimConfig, simulate

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs/gold-trendlines-monthly-1pct-20260912"
START = pd.Timestamp("2025-09-01")
END = pd.Timestamp("2026-09-01")
ASOF = pd.Timestamp("2026-09-12")
TIMEFRAMES = {"M5": 5, "M15": 15, "M30": 30, "H1": 60}


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def checked_run(df, signals, cfg, start, end, stem):
    result = simulate(df, signals, start=start, end=end, config=cfg)
    trades, daily, summary = (result[k] for k in ("trades", "daily", "summary"))
    assert abs(trades.profit.sum() - summary["net_profit"]) < 1e-6
    assert abs(daily.net_profit.sum() - summary["net_profit"]) < 1e-6
    assert abs(daily.iloc[-1].end_equity - summary["final_equity"]) < 1e-6
    assert ((cfg.start_equity + trades.profit.cumsum() - trades.equity_after).abs() < 1e-6).all()
    assert (trades.entry_time.dt.date == trades.exit_time.dt.date).all()
    assert (trades.exit_time >= trades.entry_time).all()
    if len(trades):
        before = cfg.start_equity + trades.profit.cumsum().shift(fill_value=0)
        planned_loss = ((trades.entry - trades.sl) * trades.side + cfg.slippage) * cfg.contract_size * trades.lots + trades.commission
        assert (planned_loss <= before * cfg.risk + 1e-6).all()
    trades.to_csv(OUT / f"{stem}-trades.csv", index=False)
    daily.to_csv(OUT / f"{stem}-daily.csv", index=False)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = replace(SimConfig(), risk=.01)
    manifest = dict(config=asdict(cfg), start=str(START), end_exclusive=str(END),
                    asof_exclusive=str(ASOF), candidate="lux_trendline", data={},
                    source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (Path(__file__), Path(__file__).with_name("candidates.py"),
                                             Path(__file__).with_name("simulator.py"))})
    monthly, fresh, summaries = [], [], []
    for tf, minutes in TIMEFRAMES.items():
        path = ROOT / f"data/gold-research-{tf.lower()}-20260912.csv"
        df = pd.read_csv(path, parse_dates=["time"])
        assert df.time.is_monotonic_increasing and not df.time.duplicated().any()
        assert df.time.min() < START - pd.Timedelta(days=14)
        assert df.time.max() >= ASOF - pd.Timedelta(days=1)
        previous = df.time.shift()
        gaps = ((df.time - previous) > pd.Timedelta(minutes=minutes)) & (df.time.dt.date == previous.dt.date)
        gaps &= (df.time >= START) & (df.time < ASOF) & (previous.dt.hour >= 7) & (df.time.dt.hour < 20)
        manifest["data"][tf] = dict(path=str(path.relative_to(ROOT)),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bars=len(df),
            first=str(df.time.min()), last=str(df.time.max()),
            daytime_gaps=[dict(previous=str(previous[i]), following=str(df.time[i])) for i in df.index[gaps]])
        signals = build_signals(df, "lux_trendline", minutes)
        continuous = checked_run(df, signals, cfg, START, END, f"{tf}-continuous")
        summaries.append(dict(timeframe=tf, mode="continuous", **continuous["summary"]))
        daily = continuous["daily"].copy()
        trades = continuous["trades"].copy()
        daily["month"] = pd.to_datetime(daily.date).dt.strftime("%Y-%m")
        trades["month"] = trades.exit_time.dt.strftime("%Y-%m")
        for i in range(13):
            start = START + pd.DateOffset(months=i)
            end = min(start + pd.DateOffset(months=1), ASOF)
            label = start.strftime("%Y-%m")
            if start < END:
                d = daily[daily.month == label]
                t = trades[trades.month == label]
                row = dict(timeframe=tf, month=label, net_profit=float(d.net_profit.sum()),
                           start_equity=float(d.iloc[0].start_equity), end_equity=float(d.iloc[-1].end_equity),
                           trades_count=len(t), min_equity=float(d.min_equity.min()),
                           worst_day_loss_pct=float(d.worst_loss.max()/cfg.loss_baseline*100))
                row["return_pct"] = row["net_profit"] / row["start_equity"] * 100
                monthly.append(row)
            independent = checked_run(df, signals, cfg, start, end, f"{tf}-fresh-{label}")
            fresh.append(dict(timeframe=tf, month=label, partial_month=start >= END,
                              **independent["summary"]))
        assert abs(sum(r["net_profit"] for r in monthly if r["timeframe"] == tf) - continuous["summary"]["net_profit"]) < 1e-6
        print(tf, "continuous year", continuous["summary"]["net_profit"],
              "last trade", continuous["summary"]["last_trade"], flush=True)
    for name, rows in (("continuous-monthly", monthly), ("fresh-monthly", fresh), ("continuous-summary", summaries)):
        save_json(OUT / f"{name}.json", rows)
        pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False)
    save_json(OUT / "manifest.json", manifest)
    lines = ["# Gold trendline breakouts: monthly results at 1% risk", "",
             "Tested on 12 September 2026. The 12 completed calendar months are September 2025 through August 2026. September 2026 through the 11th is a separate partial-month result. Every timeframe is a separate hypothetical $10,000 account; these are not simultaneous positions in a shared account.", "",
             "The existing unfiltered LuxAlgo-style length14 / multiplier1 / ATR trendline candidate is unchanged: first confirmed close above resistance buys, first close below support sells. Wick-only crossings do not qualify. Pivot confirmation waits 14 bars, with no backpainted entries. No EMA200, TRAMA or RSI filter. Stops are 1.5 ATR, targets 2R from signal close, maximum holding time 180 minutes (36 M5 / 12 M15 / 6 M30 / 3 H1 bars). Gaps and trading costs can change the executed reward/risk ratio.", "",
             "Risk is up to 1% of current cash equity per trade, initially $100. Lot rounding, a 1-lot cap and remaining loss headroom can reduce actual risk. Internal buffers remain 3% daily / 6% static total; the model separately checks the user-confirmed external 4% / 8%. This does not change the live risk setting or enable this strategy live.", "",
             "Entries use the next available bar open between 07:00 and 18:59, with forced closing from 20:00, one position at a time. All times and the daily reset use dataset timestamps. Base costs remain a $0.30/ounce spread floor (or recorded spread if higher), $7/lot round-trip commission and $0.03/ounce adverse slippage on market fills. Recorded spread above $0.60 blocks new entries. Costs and exact firm rules are not independently verified.", "",
             "## One account carried through all 12 months", "",
             "Dollar P&L after modeled costs. Balance, risk sizing and the original $9,400 loss floor carry forward. Each cell shows net P&L and closed trade count. Zero with no trades can mean the account has insufficient loss headroom for the minimum lot; it does not mean the strategy had a flat month of trading.", "",
             "| Month | M5 | M15 | M30 | H1 |", "|---|---:|---:|---:|---:|"]
    for i in range(12):
        label = (START + pd.DateOffset(months=i)).strftime("%Y-%m")
        values = [next(r for r in monthly if r["timeframe"] == tf and r["month"] == label) for tf in TIMEFRAMES]
        lines.append("| " + label + " | " + " | ".join(f"${r['net_profit']:+.2f} ({r['trades_count']})" for r in values) + " |")
    lines += ["| **Year total** | " + " | ".join(f"**${r['net_profit']:+.2f}**" for r in summaries) + " |", "",
              "| Timeframe | Final equity | Year trades | Profit factor | Float peak-to-trough DD | Worst day loss | Last trade |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for r in summaries:
        lines.append(f"| {r['timeframe']} | ${r['final_equity']:.2f} | {r['trades_count']} | {r['profit_factor']:.3f} | {r['max_float_dd_pct']:.2f}% | {r['worst_day_loss_pct']:.2f}% | {r['last_trade']} |")
    lines += ["", "Drawdown above is the maximum floating peak-to-trough dollar decline divided by the starting $10,000. It can exceed 6% after accumulated profits without crossing a static $9,400 floor. It is not a trailing-rule compliance measurement.", "",
              "## Fresh $10,000 account each month", "",
              "These independent monthly starts show later-month behavior even if the continuous account stopped earlier. Each month resets balance and loss buffers; profits are not carried forward. Do not add these cells and call the sum one account's yearly return. A $100 gain/loss is +1%/-1% of the monthly starting account. Parentheses contain closed trade counts.", "",
              "| Month | M5 | M15 | M30 | H1 |", "|---|---:|---:|---:|---:|"]
    for i in range(13):
        label = (START + pd.DateOffset(months=i)).strftime("%Y-%m")
        values = [next(r for r in fresh if r["timeframe"] == tf and r["month"] == label) for tf in TIMEFRAMES]
        display = label if i < 12 else label + " (through 11th)"
        lines.append("| " + display + " | " + " | ".join(f"${r['net_profit']:+.2f} ({r['trades_count']})" for r in values) + " |")
    lines += ["", "| Timeframe | Profitable completed months / 12 | Months touching below $9,410 | Worst month | Best month |",
              "|---|---:|---:|---:|---:|"]
    for tf in TIMEFRAMES:
        values = [r for r in fresh if r["timeframe"] == tf and not r["partial_month"]]
        lines.append(f"| {tf} | {sum(r['net_profit'] > 0 for r in values)} | {sum(r['min_equity'] < 9410 for r in values)} | ${min(r['net_profit'] for r in values):+.2f} | ${max(r['net_profit'] for r in values):+.2f} |")
    lines += ["", "## Verification and limits", "",
              f"All 56 simulations reconciled trade P&L, cumulative equity, daily P&L and reported ending equity. Planned stop loss including fees was checked against the 1% budget. No trade crossed a calendar date. Modeled external 4%/8% breach runs: {sum(r['firm_breach'] for r in summaries + fresh)}. Internal daily-halt events across these overlapping runs: {sum(r['internal_daily_halts'] for r in summaries + fresh)}. Risk guards restrict entries rather than inventing fills at a loss threshold.", "",
              "The same OHLC adverse-first approximation is used on every timeframe; a stop wins when both stop and target lie inside a bar. Larger bars leave more unknown intrabar ordering. No lower-timeframe or real-tick replay was used to resolve M30/H1 fills. A 1% target risk is not a guarantee against gaps or actual firm-rule breaches. [MetaQuotes on OHLC testing](https://www.mql5.com/en/docs/runtime/testing).", "",
              "Data spans the year with prior warmup, but missing intervals remain. Same-day daytime gaps within the requested span:", ""]
    for tf, data in manifest["data"].items():
        gaps = "; ".join(f"{g['previous']} to {g['following']}" for g in data["daytime_gaps"]) or "none found"
        lines.append(f"- {tf}: {data['first']} to {data['last']}; gaps: {gaps}.")
    lines += ["", "The historical feed is MT5 XAUUSD, not the OANDA screenshot feed. Pivot/tie and TradingView parity are not certified. Firm reset timezone, static-versus-trailing rules, news restrictions and real account charges remain unresolved. The results are historical tests, not proof of future profitability.", "",
              "Run `.venv\\Scripts\\python.exe -m research.gold_intraday.run_monthly_trendlines` to reproduce. CSV/JSON monthly tables, every trade and daily ledger, data hashes, source hashes and configuration are in `logs/gold-trendlines-monthly-1pct-20260912/`. Prior methodology and source notes: [original study](2026-09-12-gold-intraday-results.md).", ""]
    report = ROOT / "docs/2026-09-12-gold-trendlines-monthly-1pct.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
