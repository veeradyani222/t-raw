"""Run the frozen offline gold study: python -m research.gold_intraday.run_study.

The first eleven months rank M5/M15 candidates without final-month performance.
All results are retained. M1 is reported for the recent month only because
the broker history does not contain a complete year.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import pandas as pd

from .candidates import CANDIDATES, build_signals
from .simulator import SimConfig, simulate

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "logs/gold-intraday-20260912"
YEAR = pd.Timestamp("2025-09-12")
MONTH = pd.Timestamp("2026-08-12")
END = pd.Timestamp("2026-09-12")


def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def data_and_signals():
    frames, requests, audit = {}, {}, {}
    for tf, minutes in (("M1", 1), ("M5", 5), ("M15", 15)):
        path = ROOT / f"data/gold-research-{tf.lower()}-20260912.csv"
        df = pd.read_csv(path, parse_dates=["time"])
        assert df.time.is_monotonic_increasing and not df.time.duplicated().any()
        assert (df.tick_volume > 0).all()
        assert df.time.max() >= END-pd.Timedelta(days=1)
        frames[tf] = df
        audit[tf] = dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         bars=len(df), first=str(df.time.min()), last=str(df.time.max()),
                         history_spans_year=bool(df.time.min() <= YEAR-pd.Timedelta(days=7)),
                         month_bars=int(((df.time >= MONTH) & (df.time < END)).sum()),
                         year_bars=int(((df.time >= YEAR) & (df.time < END)).sum()),
                         observed_spread_price_median=float(df.spread.median()*.01))
        previous = df.time.shift()
        gaps = ((df.time-previous) > pd.Timedelta(minutes=minutes)) & (df.time.dt.date == previous.dt.date)
        gaps &= (df.time >= YEAR) & (df.time < END) & (previous.dt.hour >= 7) & (df.time.dt.hour < 20)
        audit[tf]["daytime_gaps"] = [dict(previous=str(previous[i]), following=str(df.time[i]))
                                    for i in df.index[gaps]]
        for name in CANDIDATES:
            requests[tf, name] = build_signals(df, name, minutes)
        print("Prepared", tf, len(df), "bars and", len(CANDIDATES), "candidates", flush=True)
    return frames, requests, audit


def evaluate(frames, requests, tf, name, window, start, end, config, tag):
    result = simulate(frames[tf], requests[tf, name], start=start, end=end, config=config)
    summary = result["summary"]
    assert abs(result["trades"].profit.sum()-summary["net_profit"]) < 1e-6
    assert abs(config.start_equity+summary["net_profit"]-summary["final_equity"]) < 1e-6
    row = dict(timeframe=tf, candidate=name, description=CANDIDATES[name], window=window,
               start=str(start), end_exclusive=str(end), risk=config.risk, cost_profile=tag, **summary)
    stem = OUT/f"{tag}-{tf}-{name}-{window}"
    result["trades"].to_csv(str(stem)+"-trades.csv", index=False)
    result["daily"].to_csv(str(stem)+"-daily.csv", index=False)
    print(f"{tag:10} {tf:3} {name:21} {window:16} trades={row['trades_count']:4} "
          f"net={row['net_profit']:+8.2f} floatDD={row['max_float_dd_pct']:5.2f}% "
          f"worstday={row['worst_day_loss_pct']:4.2f}% halt={row['internal_total_halt']}", flush=True)
    return row


def screen(frames, requests, audit):
    cfg = SimConfig()
    rows = []
    # Freeze ranking without any final-month P&L in the selection calculation.
    for tf in ("M5", "M15"):
        assert audit[tf]["history_spans_year"]
        for name in CANDIDATES:
            rows.append(evaluate(frames, requests, tf, name, "selection_11mo", YEAR, MONTH, cfg, "base"))
    viable = [r for r in rows if r["net_profit"] > 0 and r["profit_factor"] >= 1.1
              and r["trades_count"] >= 80 and not r["firm_breach"] and r["internal_total_halt"] is None]
    viable.sort(key=lambda r: r["net_profit"], reverse=True)
    frozen = [{"timeframe": r["timeframe"], "candidate": r["candidate"],
               "selection_net": r["net_profit"]} for r in viable[:3]]
    save_json(OUT/"frozen-selection.json", frozen)
    save_json(OUT/"selection-results.json", rows)
    print("FROZEN first-11-month shortlist:", frozen, flush=True)
    for tf in ("M1", "M5", "M15"):
        for name in CANDIDATES:
            if audit[tf]["history_spans_year"]:
                rows.append(evaluate(frames, requests, tf, name, "year", YEAR, END, cfg, "base"))
            rows.append(evaluate(frames, requests, tf, name, "month", MONTH, END, cfg, "base"))
    save_json(OUT/"screen-results.json", rows)
    pd.DataFrame(rows).to_csv(OUT/"screen-results.csv", index=False)
    return rows, frozen


def stress(frames, requests, rows, frozen):
    # Stress the preselected candidates plus the user's M15 trendline idea.
    chosen = {(r["timeframe"], r["candidate"]) for r in frozen}
    origins = {pair: "first_11_month_selection" for pair in chosen}
    chosen.update({("M15", "lux_trendline"), ("M15", "lux_trendline_trend")})
    for pair in chosen:
        origins.setdefault(pair, "user_requested_indicator")
    # Also audit any other candidate profitable in both requested windows;
    # label these explicitly as post-hoc candidates, not held-out selections.
    for tf in ("M5", "M15"):
        for name in CANDIDATES:
            windows = [r for r in rows if r["timeframe"] == tf and r["candidate"] == name
                       and r["window"] in ("year", "month")]
            if len(windows) == 2 and all(r["net_profit"] > 0 and r["internal_total_halt"] is None
                                         and not r["firm_breach"] for r in windows):
                chosen.add((tf, name))
                origins.setdefault((tf, name), "post_hoc_positive_year_and_month")
    results, starts = [], []
    for tf, name in sorted(chosen):
        for tag, cfg in (("cost_stress", replace(SimConfig(), spread_floor=.60, commission_per_lot=10., slippage=.10)),
                         ("risk_0p5", replace(SimConfig(), risk=.005))):
            for window, start in (("year", YEAR), ("month", MONTH)):
                row = evaluate(frames, requests, tf, name, window, start, END, cfg, tag)
                row["selection_origin"] = origins[tf, name]
                results.append(row)
        for risk in (.0025, .005):
            for offset in range(12):
                start = YEAR+pd.DateOffset(months=offset)
                row = evaluate(frames, requests, tf, name, f"start_{start:%Y%m%d}", start, END,
                               replace(SimConfig(), risk=risk), f"reset_{risk:g}")
                starts.append(row)
                row["selection_origin"] = origins[tf, name]
    save_json(OUT/"stress-results.json", results)
    save_json(OUT/"fresh-start-results.json", starts)
    pd.DataFrame(results).to_csv(OUT/"stress-results.csv", index=False)
    pd.DataFrame(starts).to_csv(OUT/"fresh-start-results.csv", index=False)
    return results, starts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "stress", "all"), default="all")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    frames, requests, audit = data_and_signals()
    source_paths = [Path(__file__), Path(__file__).with_name("candidates.py"),
                    Path(__file__).with_name("simulator.py")]
    manifest = dict(audit=audit, candidates=CANDIDATES, primary_config=asdict(SimConfig()),
                    source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in source_paths},
                    selection_start=str(YEAR), holdout_start=str(MONTH), end_exclusive=str(END))
    if args.phase == "stress":
        previous_manifest = json.loads((OUT/"manifest.json").read_text())
        if previous_manifest != manifest:
            raise RuntimeError("Study inputs/code changed since screening; rerun --phase all.")
    else:
        save_json(OUT/"manifest.json", manifest)
    if args.phase in ("screen", "all"):
        rows, frozen = screen(frames, requests, audit)
    else:
        rows = json.loads((OUT/"screen-results.json").read_text())
        frozen = json.loads((OUT/"frozen-selection.json").read_text())
    if args.phase in ("stress", "all"):
        stress(frames, requests, rows, frozen)
    print("Saved research results to", OUT, flush=True)


if __name__ == "__main__":
    main()
