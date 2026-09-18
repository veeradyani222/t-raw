"""Fixed pair comparison for the hour0 / 12-hour long strategy, offline only."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.jpy_session_recheck import simulate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"logs/jpy-pair-screen-20260913"
END = pd.Timestamp("2026-09-01")
PAIRS = ("EURJPY", "GBPJPY", "NZDJPY", "CHFJPY", "AUDJPY")


def cached(symbol):
    paths = [ROOT/f"data/session-{symbol.lower()}-h1-older-20260913.csv",
             ROOT/f"data/{symbol.lower()}-h1.csv",
             ROOT/f"data/session-{symbol.lower()}-h1-recent-20260913.csv"]
    cols = ["time", "open", "high", "low", "close", "tick_volume"]
    d = pd.concat([pd.read_csv(p, parse_dates=["time"])[cols] for p in paths])
    d = d.drop_duplicates("time", keep="last").sort_values("time")
    return d[d.time < END].reset_index(drop=True), paths


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    usd, fx_paths = cached("USDJPY")
    fx = usd[["time", "close"]].rename(columns={"close": "fx"})
    fx["fx_previous"] = fx.fx.shift()
    audit, rows = {}, []
    for symbol in PAIRS:
        if symbol == "AUDJPY":
            d, paths = cached(symbol)
        else:
            path = ROOT/f"data/session-{symbol.lower()}-h1-screen-20260913.csv"
            if not path.exists():
                audit[symbol] = dict(skipped="No retrieved history")
                continue
            paths = [path]
            d = pd.read_csv(path, parse_dates=["time"])
            d = d[d.time < END].reset_index(drop=True)
        assert d.time.is_monotonic_increasing and not d.time.duplicated().any()
        assert np.isfinite(d[["open", "high", "low", "close"]]).all().all()
        assert (d.high >= d[["open", "close", "low"]].max(axis=1)).all()
        assert (d.low <= d[["open", "close"]].min(axis=1)).all()
        if d.empty or d.time.max() < END-pd.Timedelta(days=4):
            audit[symbol] = dict(skipped="History does not reach common endpoint")
            continue
        before = len(d)
        d = pd.merge_asof(d, fx, on="time", tolerance=pd.Timedelta(hours=3)).dropna(subset=["fx", "fx_previous"]).reset_index(drop=True)
        years = [y for y in range(2016, 2026) if (d.time < pd.Timestamp(y, 1, 1)).sum() >= 15]
        audit[symbol] = dict(first=str(d.time.min()), last=str(d.time.max()), bars=len(d),
                             fx_rows_dropped=before-len(d), full_years=years,
                             sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        windows = [(str(y), pd.Timestamp(y, 1, 1), pd.Timestamp(y+1, 1, 1), "calendar_year") for y in years]
        windows += [("last_12_months", END-pd.DateOffset(years=1), END, "recent"),
                    ("last_month", END-pd.DateOffset(months=1), END, "recent")]
        for profile, spread in (("base", 2.5), ("wide", 5.)):
            for label, start, end, kind in windows:
                result, t = simulate(d, symbol, 0, start, end, spread_pips=spread)
                assert abs(t.profit.sum()-result["net"]) < 1e-6
                rows.append(dict(symbol=symbol, profile=profile, spread_pips=spread,
                                 label=label, kind=kind, start=str(start), end_exclusive=str(end), **result))
                t.to_csv(OUT/f"{symbol}-{profile}-{label}-trades.csv", index=False)
        print(symbol, "completed", len(years), "full years under both cost profiles", flush=True)
    overview = []
    for symbol in PAIRS:
        if "skipped" in audit[symbol]:
            continue
        entry = dict(symbol=symbol)
        for profile in ("base", "wide"):
            annual = [r for r in rows if r["symbol"] == symbol and r["profile"] == profile and r["kind"] == "calendar_year"]
            year = next(r for r in rows if r["symbol"] == symbol and r["profile"] == profile and r["label"] == "last_12_months")
            month = next(r for r in rows if r["symbol"] == symbol and r["profile"] == profile and r["label"] == "last_month")
            entry.update({f"{profile}_mean_annual": float(np.mean([r["net"] for r in annual])),
                          f"{profile}_median_annual": float(np.median([r["net"] for r in annual])),
                          f"{profile}_profitable_years": sum(r["net"] > 0 for r in annual),
                          f"{profile}_halted_years": sum(r["permanent_halt"] is not None for r in annual),
                          f"{profile}_year_net": year["net"], f"{profile}_month_net": month["net"],
                          f"{profile}_year_halt": year["permanent_halt"], "years": len(annual)})
        overview.append(entry)
    payload = dict(audit=audit, overview=overview, rows=rows,
                   fx_source_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fx_paths},
                   code_hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (Path(__file__), ROOT/"research/jpy_session_recheck.py", ROOT/"trader/risk.py")})
    (OUT/"results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT/"all-results.csv", index=False)
    pd.DataFrame(overview).to_csv(OUT/"overview.csv", index=False)
    lines = ["# Other pairs for the 12-hour session strategy — 13 September 2026", "",
             "Fixed candidates before results: EURJPY, GBPJPY, NZDJPY, CHFJPY. AUDJPY is the reference. All use the same hour0 H1 closed-bar long signal, 2 times simple ATR14 stop, no take-profit, and 12 elapsed hours maximum holding until the next executable bar close. No timing or stop parameters were optimized per pair. A completed hour0 candle entry is modeled at its close, not at exactly midnight. Dataset/broker clock is retained; its market-session/DST interpretation is not independently verified.", "",
             "Each simulation starts a separate $10,000 account, 1% modeled balance risk, maximum1 lot and 0.01 lot steps, with the existing $300 daily / $600 static total closed-balance guard. The base spread is 2.5 pips for every pair; wide-spread sensitivity uses5 pips. Both include assumed $7/lot round-trip commission and0.1 pip slippage per market fill, plus JPY-to-USD conversion. Swap/conversion spread and floating-equity risk checks are not included. These are controlled cost assumptions, not verified pair-specific execution costs.", "",
             "Latest year means September1,2025–August31,2026. Latest month means August2026. Calendar-year averages use separate annual starts and include halted years. AUDJPY is rerun at the higher common costs, so its numbers differ from the earlier 1.5-pip report. All accounts are standalone; no shared-account portfolio or payout model is tested here.", "",
             "## Comparison", "", "| Pair | Mean annual net: 2.5 pips | Profitable years | Mean annual net: 5 pips | Last year: 2.5 pips | Last year: 5 pips | August2026: 2.5 pips |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for r in overview:
        lines.append(f"| {r['symbol']} | ${r['base_mean_annual']:+.2f} | {r['base_profitable_years']}/{r['years']} | ${r['wide_mean_annual']:+.2f} | ${r['base_year_net']:+.2f} | ${r['wide_year_net']:+.2f} | ${r['base_month_net']:+.2f} |")
    lines += ["", "## Risk-stop and median results", "", "| Pair | Median annual net: base | Halted years: base | Profitable years: wide | Halted years: wide | Recent year halted: base / wide |",
              "|---|---:|---:|---:|---:|---|"]
    for r in overview:
        lines.append(f"| {r['symbol']} | ${r['base_median_annual']:+.2f} | {r['base_halted_years']}/{r['years']} | {r['wide_profitable_years']}/{r['years']} | {r['wide_halted_years']}/{r['years']} | {r['base_year_halt'] or 'No'} / {r['wide_year_halt'] or 'No'} |")
    lines += ["", "## All annual attempts", "", "| Pair | Year | Base net | Wide-spread net |", "|---|---|---:|---:|"]
    for symbol in PAIRS:
        if "skipped" in audit[symbol]:
            continue
        for year in audit[symbol]["full_years"]:
            a = next(r for r in rows if r["symbol"] == symbol and r["label"] == str(year) and r["profile"] == "base")
            b = next(r for r in rows if r["symbol"] == symbol and r["label"] == str(year) and r["profile"] == "wide")
            lines.append(f"| {symbol} | {year} | ${a['net']:+.2f} | ${b['net']:+.2f} |")
    lines += ["", "## Interpretation and source context", "",
              "This is an exploratory historical pair screen. Choosing the best-looking pair afterward creates selection bias, even without a parameter grid. A strong recent year alone is insufficient; the annual median, losing years and cost sensitivity matter. All these long positions sell JPY, so combining them increases shared yen exposure rather than establishing independent returns. No correlation or joint-account drawdown test was performed.", "",
              "Time-of-day currency effects have been documented in primary research, including depreciation during a currency's local trading hours. This motivates testing a time-window hypothesis; it does not establish that our broker's hour0, 12-hour long strategy works for any particular pair. [Breedon and Ranaldo, Intraday Patterns in FX Returns and Order Flow](https://onlinelibrary.wiley.com/doi/10.1111/jmcb.12032).", "",
              "The simulator's JPY profit conversion follows the contract-size/price-change arithmetic, with an approximate historical conversion rate for cross-pair intrabar exits. [MetaQuotes profit formulas](https://www.mql5.com/en/book/automation/experts/experts_ordercalcprofit). Stop-first OHLC fills, previous-USDJPY-close conversion on cross-pair stops and closed-balance guards do not certify real execution or prop-firm compliance. Data spans and dropped FX-conversion rows are recorded in the manifest; history is not certified gap-free.", "",
              "No live strategy, setting or order was changed. Reproduce with `.venv\\Scripts\\python.exe -m research.jpy_pair_screen`. Every trade, attempted result, data/source hash and summary is in `logs/jpy-pair-screen-20260913/`.", ""]
    path = ROOT/"docs/2026-09-13-jpy-pair-screen.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(pd.DataFrame(overview).to_string(index=False), flush=True)
    print(path, flush=True)


if __name__ == "__main__":
    main()
