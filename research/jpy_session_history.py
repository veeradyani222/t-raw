"""Ten calendar years and monthly results for the identified JPY candidates."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.jpy_session_recheck import simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"logs/jpy-session-history-20260913"
END = pd.Timestamp("2026-09-05")
PAIRS = {"AUDJPY": (0, 1.5), "USDJPY": (6, 1.)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames, audit = {}, {}
    for symbol in ("USDJPY", "AUDJPY"):
        paths = [ROOT/f"data/session-{symbol.lower()}-h1-older-20260913.csv",
                 ROOT/f"data/{symbol.lower()}-h1.csv",
                 ROOT/f"data/session-{symbol.lower()}-h1-recent-20260913.csv"]
        cols = ["time", "open", "high", "low", "close", "tick_volume"]
        d = pd.concat([pd.read_csv(p, parse_dates=["time"])[cols] for p in paths])
        d = d.drop_duplicates("time", keep="last").sort_values("time")
        d = d[d.time < END].reset_index(drop=True)
        assert d.time.is_monotonic_increasing and not d.time.duplicated().any()
        assert np.isfinite(d[cols[1:]].to_numpy()).all() and (d.tick_volume > 0).all()
        frames[symbol] = d
        audit[symbol] = dict(first=str(d.time.min()), last=str(d.time.max()), bars=len(d),
                             source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    fx = frames["USDJPY"][["time", "close"]].rename(columns={"close": "fx"})
    fx["fx_previous"] = fx.fx.shift()
    for symbol, d in frames.items():
        frames[symbol] = pd.merge_asof(d, fx, on="time", tolerance=pd.Timedelta(hours=3)).dropna(subset=["fx", "fx_previous"]).reset_index(drop=True)
        audit[symbol]["rows_dropped_without_fx"] = len(d)-len(frames[symbol])
    results = []

    def run(symbol, label, start, end, category):
        hour, spread = PAIRS[symbol]
        s, t = simulate(frames[symbol], symbol, hour, start, end, spread_pips=spread)
        row = dict(symbol=symbol, hour=hour, spread_pips=spread, category=category,
                   label=label, start=str(start), end_exclusive=str(end), **s)
        t.to_csv(OUT/f"{symbol}-{category}-{label}-trades.csv", index=False)
        results.append(row)
        return row, t

    for symbol in PAIRS:
        for year in range(2016, 2026):
            start, end = pd.Timestamp(year, 1, 1), pd.Timestamp(year+1, 1, 1)
            assert (frames[symbol].time < start).sum() >= 15
            r, _ = run(symbol, str(year), start, end, "calendar_year")
            print(symbol, year, round(r["net"], 2), "halt", r["permanent_halt"], flush=True)
        run(symbol, "2026", pd.Timestamp("2026-01-01"), END, "ytd")
        # Both plausible meanings of 'last year monthwise', labeled separately.
        for name, start, end in (("calendar_2025", pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")),
                                 ("latest_12_complete_months", pd.Timestamp("2025-09-01"), pd.Timestamp("2026-09-01"))):
            summary, trades = run(symbol, name, start, end, "continuous_window")
            accumulated = 0.
            for month in pd.date_range(start, end, freq="MS", inclusive="left"):
                stop = month + pd.DateOffset(months=1)
                t = trades[(trades.exit_time >= month) & (trades.exit_time < stop)]
                net = float(t.profit.sum())
                accumulated += net
                results.append(dict(symbol=symbol, category=name+"_continuous_month", label=f"{month:%Y-%m}",
                                    net=net, trades=len(t), ending_balance=10000+accumulated))
                run(symbol, f"{month:%Y-%m}", month, stop, name+"_fresh_month")
            assert abs(accumulated-summary["net"]) < 1e-6
    averages = {}
    for symbol in PAIRS:
        r = [r for r in results if r["symbol"] == symbol and r["category"] == "calendar_year"]
        averages[symbol] = dict(years=len(r), mean_net=float(np.mean([x["net"] for x in r])),
                                mean_return_pct=float(np.mean([x["net"] for x in r])/100),
                                profitable_years=sum(x["net"] > 0 for x in r),
                                halted_years=sum(x["permanent_halt"] is not None for x in r))
    payload = dict(audit=audit, candidates=PAIRS, averages=averages, results=results,
                   code_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (Path(__file__), ROOT/"research/jpy_session_recheck.py", ROOT/"trader/risk.py")})
    (OUT/"results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    pd.DataFrame(results).to_csv(OUT/"results.csv", index=False)
    lines = ["# AUDJPY and USDJPY session strategy history — 13 September 2026", "",
             "Candidates: AUDJPY H1 signal hour0 and USDJPY H1 signal hour6, long only, 2 times ATR14 stop, no take profit, exit after 12 elapsed hours unless stopped first. Signals use the completed H1 bar with that opening-hour label; executable entry is modeled at its close plus costs. Thus hour0 is not an order precisely at midnight. Times are dataset/broker labels, not independently verified local/UTC trading-session times.", "",
             "GitHub main was checked remotely at f41d13e. The archived live configuration at commit665430a enabled USDJPY hour6, not AUDJPY. AUDJPY hour0 is the research candidate checked here; its former live deployment was not found. The pure archived strategy matched 160 sampled signals in the initial recheck. Nothing was restored to the live registry.", "",
             "All yearly and fresh-month runs start flat at $10,000 with 1% modeled balance risk, maximum1 lot, 0.01 lot steps, and existing $300 daily / $600 static total closed-balance guard. Commission is assumed $7/lot round-trip, slippage0.1 pip per market fill, spread1.5 pips AUDJPY / 1 pip USDJPY. These are assumptions, not verified account costs. Historical zero bar-spread fields are not treated as free execution. No monthly withdrawals.", "",
             "JPY P&L is converted to USD using USDJPY: same-symbol exit price for USDJPY and contemporaneous USDJPY close for AUDJPY scheduled exits, previous close for AUDJPY intrabar stops. Currency-conversion spread is not modeled. This replaces the old harness's fixed $10/pip-per-lot shortcut. Both pairs have 100,000-unit contracts. [MetaQuotes profit formulas](https://www.mql5.com/en/book/automation/experts/experts_ordercalcprofit).", "",
             "## Full calendar years", "", "Each row independently starts January1 and ends December31. A halted account stays stopped until its row ends; the next year is a separate fresh account.", "",
             "| Year | AUDJPY hour0 net | USDJPY hour6 net |", "|---|---:|---:|"]
    for year in range(2016, 2026):
        values = [next(r for r in results if r["symbol"] == symbol and r["category"] == "calendar_year" and r["label"] == str(year)) for symbol in PAIRS]
        lines.append(f"| {year} | ${values[0]['net']:+.2f} | ${values[1]['net']:+.2f} |")
    lines += ["| **Mean annual net** | " + " | ".join(f"**${averages[s]['mean_net']:+.2f} ({averages[s]['mean_return_pct']:+.2f}%)**" for s in PAIRS) + " |", ""]
    for symbol, a in averages.items():
        lines.append(f"- {symbol}: {a['profitable_years']}/10 profitable calendar years; {a['halted_years']}/10 internally halted. Arithmetic yearly mean includes all losing and halted years.")
    lines += ["", "2026 is partial and excluded from the averages:", "", "| Jan1–Sep4, 2026 | Net |", "|---|---:|"]
    for symbol in PAIRS:
        row = next(r for r in results if r["symbol"] == symbol and r["category"] == "ytd")
        lines.append(f"| {symbol} | ${row['net']:+.2f} |")
    for name, title in (("latest_12_complete_months", "Latest 12 complete months: September2025–August2026"),
                         ("calendar_2025", "January–December2025")):
        lines += ["", "## " + title, "",
                  "The continuous columns use one $10,000 account for the window, with profits/losses and positions carried forward. Fresh columns start each individual month at $10,000; they cannot be summed as a single account's return. A zero with zero trades may reflect a prior permanent halt.", "",
                  "| Month | AUDJPY continuous net (trades) | USDJPY continuous net (trades) | AUDJPY fresh-month net | USDJPY fresh-month net |",
                  "|---|---:|---:|---:|---:|"]
        months = sorted({r["label"] for r in results if r["category"] == name+"_continuous_month"})
        for month in months:
            c = [next(r for r in results if r["symbol"] == symbol and r["category"] == name+"_continuous_month" and r["label"] == month) for symbol in PAIRS]
            f = [next(r for r in results if r["symbol"] == symbol and r["category"] == name+"_fresh_month" and r["label"] == month) for symbol in PAIRS]
            lines.append(f"| {month} | ${c[0]['net']:+.2f} ({c[0]['trades']}) | ${c[1]['net']:+.2f} ({c[1]['trades']}) | ${f[0]['net']:+.2f} | ${f[1]['net']:+.2f} |")
    lines += ["", "## Limitations and verification", "",
              "The common history cutoff is September4, 2026 because AUDJPY's available feed stops there; USDJPY's additional week was not used to create an unequal comparison. Older history was fetched for December2015 onward so January2016 has indicator warmup. Finite OHLC, unique chronological timestamps and available FX conversion were checked; history is not certified gap-free. No exchange-rate row more than three hours stale is carried forward.", "",
              "The model handles stop-before-time-exit priority, adverse opening gaps, spread, fees and the 12-hour timer. Risk guards use closed balance and therefore do not certify floating-equity compliance. Swap and conversion spreads are omitted; rare missing-bar/closed-market delays can create overnight exposure. A monthly or annual terminal exit is an artificial mark. Wider-spread sensitivity from the initial recheck is separate from this requested historical table; these annual numbers are not evidence of stress-tested profitability.", "",
              "Every run reconciles trade profits to ending balance, and continuous monthly rows reconcile to their window total. Unit checks cover 12-hour exit timing, JPY/USD conversion and commission charging. Raw yearly/monthly trade logs, tables, source/data hashes and both interpretations of 'last year monthwise' are in `logs/jpy-session-history-20260913/`. Reproduce with `.venv\\Scripts\\python.exe -m research.jpy_session_history`.", ""]
    report = ROOT/"docs/2026-09-13-jpy-session-history.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(averages, indent=2), flush=True)
    print(report, flush=True)


if __name__ == "__main__":
    main()
