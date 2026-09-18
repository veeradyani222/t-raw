"""Offline recheck of the deleted 12-hour JPY session idea; no live registry."""
import ast
import hashlib
import json
import math
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import pandas as pd

from trader.risk import RiskGuard
from trader.strategy import Setup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs/jpy-session-recheck-20260913"
END = pd.Timestamp("2026-09-05")  # Latest common complete day for both feeds.


def signal_inputs(df, hour):
    previous = df.close.shift()
    tr = pd.concat([df.high-df.low, (df.high-previous).abs(), (df.low-previous).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    side = (df.time.dt.hour == hour) & atr.notna() & (atr > 0)
    side.iloc[:14] = False
    return side.to_numpy(), (df.close-2*atr).to_numpy()


def simulate(df, symbol, hour, start, end, *, spread_pips, commission=7., slip_pips=.1):
    side, stops = signal_inputs(df, hour)
    values = df[["open", "high", "low", "close", "fx", "fx_previous"]].to_numpy()
    times = pd.DatetimeIndex(df.time)
    guard = RiskGuard(1, .03, 0., 10000., .06)
    balance, pos, halt, trades = 10000., None, None, []
    spread, slip = spread_pips*.01, slip_pips*.01
    indices = np.flatnonzero(((times >= start) & (times < end)))

    def settle(price, rate, i, reason):
        nonlocal balance, pos
        if symbol == "USDJPY":
            rate = price
        gross = (price-pos["entry"])*100000*pos["lots"]/rate
        fees = pos["lots"]*commission
        profit = gross-fees
        balance += gross-fees/2
        trades.append(dict(entry_time=times[pos["bar"]], exit_time=times[i], entry=pos["entry"],
                           exit=price, sl=pos["sl"], lots=pos["lots"], gross=gross, fees=fees,
                           profit=profit, equity_after=balance, reason=reason))
        pos = None

    for i in indices:
        op, hi, lo, cl, fx, fx_prev = values[i]
        if pos is not None:
            if op <= pos["sl"]:
                settle(op-slip, fx_prev, i, "gap_sl")
            elif lo <= pos["sl"]:
                settle(pos["sl"]-slip, fx_prev, i, "sl")
            elif times[i]-times[pos["bar"]] >= pd.Timedelta(hours=12):
                settle(cl-slip, fx, i, "time")
        guard.on_new_bar(times[i].date(), balance)
        if guard.blown and halt is None:
            halt = times[i]
        if pos is None and side[i] and guard.may_open(0)[0]:
            entry, sl = cl+spread+slip, stops[i]
            loss_per_lot = (entry-sl+slip)*100000/fx + commission
            lots = math.floor(min(1., balance*.01/loss_per_lot)*100)/100
            if lots >= .01:
                balance -= lots*commission/2
                pos = dict(entry=entry, sl=sl, lots=lots, bar=i)
    if pos is not None:
        i = indices[-1]
        settle(values[i, 3]-slip, values[i, 4], i, "end")
    t = pd.DataFrame(trades)
    assert abs(10000+t.profit.sum()-balance) < 1e-6
    assert ((10000+t.profit.cumsum()-t.equity_after).abs() < 1e-6).all()
    p = t.profit
    eq = np.r_[10000., t.equity_after.to_numpy()]
    return dict(net=float(p.sum()), final_balance=balance, trades=len(t),
                win_rate=float((p>0).mean()*100),
                profit_factor=float(p[p>0].sum()/-p[p<0].sum()) if (p<0).any() else None,
                closed_drawdown=float((np.maximum.accumulate(eq)-eq).max()),
                permanent_halt=halt), t


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames, sources = {}, {}
    for symbol in ("USDJPY", "AUDJPY"):
        paths = [ROOT/f"data/{symbol.lower()}-h1.csv", ROOT/f"data/session-{symbol.lower()}-h1-recent-20260913.csv"]
        parts = [pd.read_csv(p, parse_dates=["time"]) for p in paths]
        cols = ["time", "open", "high", "low", "close", "tick_volume"]
        d = pd.concat([p[cols] for p in parts]).drop_duplicates("time", keep="last").sort_values("time")
        d = d[d.time < END].reset_index(drop=True)
        assert d.time.is_monotonic_increasing and not d.time.duplicated().any()
        assert (d.tick_volume > 0).all()
        frames[symbol] = d
        sources[symbol] = dict(first=str(d.time.min()), last=str(d.time.max()), bars=len(d),
                               hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    usd = frames["USDJPY"][["time", "close"]].rename(columns={"close": "fx"})
    usd["fx_previous"] = usd.fx.shift()
    for symbol, d in frames.items():
        frames[symbol] = pd.merge_asof(d, usd, on="time", tolerance=pd.Timedelta(hours=3)).dropna(subset=["fx", "fx_previous"]).reset_index(drop=True)
        sources[symbol]["rows_without_conversion_dropped"] = len(d)-len(frames[symbol])
    # Load only the original pure strategy, without registering it for live use.
    original = subprocess.check_output(["git", "show", "665430a:trader/strategies/session.py"], text=True, encoding="utf-8")
    tree = ast.parse(original)
    tree.body = [n for n in tree.body if not isinstance(n, ast.ImportFrom)]
    namespace = {"Setup": Setup, "Signal": __import__("trader.strategy", fromlist=["Signal"]).Signal}
    exec(compile(tree, "archived_session.py", "exec"), namespace)
    checks = 0
    for symbol, d in frames.items():
        for hour in (0, 6):
            side, stops = signal_inputs(d, hour)
            candidates = np.flatnonzero(side)
            chosen = candidates[np.linspace(0, len(candidates)-1, 40, dtype=int)]
            cfg = SimpleNamespace(session_atr_n=14, session_entry_hour=hour,
                                  session_stop_atr_mult=2., session_side="long", session_hold_bars=12)
            for i in chosen:
                s = namespace["compute_signal"](d.iloc[max(0, i-18):i+1], cfg)
                assert isinstance(s, Setup) and abs(s.sl-stops[i])<1e-9
                checks += 1
    rows = []
    for symbol, d in frames.items():
        for hour in (0, 6):
            windows = [(str(y), pd.Timestamp(y, 1, 1), pd.Timestamp(y+1, 1, 1)) for y in range(2018, 2026)]
            windows += [("2026_YTD", pd.Timestamp("2026-01-01"), END),
                        ("last_year", END-pd.DateOffset(years=1), END),
                        ("last_month", END-pd.DateOffset(months=1), END)]
            for name, start, end in windows:
                profiles = ("base", "spread_stress") if name in ("last_year", "last_month") else ("base",)
                for profile in profiles:
                    spread = (1. if symbol == "USDJPY" else 1.5) + (2. if profile == "spread_stress" else 0.)
                    s, t = simulate(d, symbol, hour, start, end, spread_pips=spread)
                    row = dict(symbol=symbol, signal_hour=hour, window=name, start=str(start),
                               end_exclusive=str(end), profile=profile, spread_pips=spread, **s)
                    rows.append(row)
                    t.to_csv(OUT/f"{symbol}-hour{hour}-{name}-{profile}-trades.csv", index=False)
            print(symbol, "hour", hour, "completed", flush=True)
    payload = dict(source_commit="665430a", github_main="f41d13e9ecf9a29b6ea809e166844e5bd246f043",
                   sources=sources, original_signal_checks=checks, rows=rows)
    (OUT/"results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    pd.DataFrame(rows).to_csv(OUT/"results.csv", index=False)
    print(pd.DataFrame(rows).query("window in ['last_year','last_month']")[["symbol","signal_hour","window","profile","net","permanent_halt"]].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
