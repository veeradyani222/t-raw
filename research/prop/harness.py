"""Shared prop-firm scoring harness for the 2026-10 strategy search.

ONE judge for every strategy, so results are comparable. Pure research code:
it never touches trader/ live code or MT5.

Data: data/search/<symbol>-<tf>.csv (MT5 broker-time bars, EET like
FundedNext's server day). Pull with load(symbol, tf, split=...).

Splits (anti-overfit):
    "is"  = everything before 2024-01-01  -> develop / tune here ONLY
    "oos" = 2024-01-01 onward (+ warmup)  -> LOCKED unless env PROP_OOS=1
    "all" = both                           -> also locked behind PROP_OOS=1
Final verification is the only stage allowed to set PROP_OOS=1.

Strategy interface (same idea as wf_search):
    signal_fn(df, i) -> Entry | None     # i = latest CLOSED bar; use df rows <= i only
or a precomputed list/array of Entry|None with len(df) (much faster).
Optional Entry.manage(df, i, pos) -> None | float (new stop) | "close"
lets a strategy trail stops / exit on its own logic each bar.

Accounting (fixed-dollar risk, NOT compounding): every trade risks
risk * BASELINE ($10k) dollars at the stop. That makes P&L path-independent,
so the monthly / challenge windows below are honest slices of one run.

Costs: spread (per-symbol floor or the bar's own spread, whichever is
larger, x spread_mult), slippage per fill, commission per lot round trip
(FundedNext Stellar Lite: $7/side forex & metals). P&L converted to USD with
the per-bar conversion rate (JPY via USDJPY, etc.).

Fills (conservative, matches trader.sim): positions open at bar close + cost;
stops/targets checked on later bars against high/low, STOP FIRST when both
touch in one bar; a gap through the stop fills at the bar open.

Guardrails (FundedNext Stellar Lite $10k): daily loss 4% ($400) off the
day-start balance INCLUDING floating P&L; static max loss 8% (floor $9,200).
We judge on BUFFERED versions: worst day must stay under 3% and worst
drawdown (from peak, worst intrabar) under 6%. The engine also blocks new
entries for the rest of a day once that day is down `daily_block` (3%).

    score(...) -> dict with monthly table, worst day, max DD, firm breaches,
                  challenge pass stats, and best_risk (highest risk in
                  RISKS that keeps worst day <3% and max DD <6%).
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "search"
# Round 2 (2026-10-23): the locked window is the last TWO years (Veer's call),
# matching the window the live mix was sized on. Override with PROP_OOS_START.
OOS_START = pd.Timestamp(os.environ.get("PROP_OOS_START", "2024-10-20"))
BASELINE = 10_000.0
FIRM_DAILY, FIRM_TOTAL = 0.04, 0.08          # FundedNext Stellar Lite
SAFE_DAILY, SAFE_DD = 0.03, 0.06             # our buffered judging limits
PHASE_TARGETS = (0.08, 0.04)                 # Stellar Lite phase 1 / phase 2
RISKS = (0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02)

# Per-symbol cost floors, in PRICE units (not points). Conservative.
SPREAD_FLOOR = {
    "XAUUSD": 0.30, "XAGUSD": 0.03,
    "EURUSD": 0.00010, "GBPUSD": 0.00014, "AUDUSD": 0.00012, "NZDUSD": 0.00016,
    "USDCAD": 0.00016, "USDCHF": 0.00015, "EURGBP": 0.00012, "EURCHF": 0.00016,
    "GBPCHF": 0.00025, "AUDCAD": 0.00020,
    "USDJPY": 0.012, "EURJPY": 0.020, "GBPJPY": 0.030, "AUDJPY": 0.020,
    "CHFJPY": 0.025, "NZDJPY": 0.025, "CADJPY": 0.025,
    "US30": 3.0, "US500": 0.6, "USTEC": 1.8, "DE40": 1.5,
}
INDICES = {"US30", "US500", "USTEC", "DE40"}
COMMISSION_RT = 14.0   # $ per lot round trip, FX & metals; indices 0


def _spec():
    p = DATA / "symbol_specs.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _pip(symbol):
    """Price size of one 'pip' (used only for slippage)."""
    if symbol in ("XAUUSD",):
        return 0.1
    if symbol in ("XAGUSD",):
        return 0.01
    if symbol in INDICES:
        return 1.0
    return 0.01 if symbol.endswith("JPY") else 0.0001


def _guard_split(split):
    if split not in ("is", "oos", "all"):
        raise ValueError("split must be 'is', 'oos' or 'all'")
    if split != "is" and os.environ.get("PROP_OOS") != "1":
        raise PermissionError(
            "Out-of-sample data (2024+) is LOCKED for development. Tune on "
            "split='is' only; the final verification stage unlocks it.")


def load(symbol: str, tf: str = "H1", split: str = "is",
         warmup_bars: int = 3000) -> pd.DataFrame:
    """Bars with columns time, open, high, low, close, tick_volume, spread,
    plus `conv` (multiply quote-currency P&L by this to get USD).

    split='oos' keeps `warmup_bars` before 2024-01-01 so indicators are warm;
    use df.attrs['score_from'] (passed to score() automatically) to only
    COUNT trades from 2024 on."""
    _guard_split(split)
    symbol = symbol.upper()
    df = pd.read_csv(DATA / f"{symbol.lower()}-{tf.lower()}.csv", parse_dates=["time"])
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    df = _attach_conv(df, symbol, tf)
    score_from = None
    if split == "is":
        df = df[df.time < OOS_START]
    elif split == "oos":
        first = int(np.searchsorted(df.time.values, OOS_START.to_datetime64()))
        df = df.iloc[max(0, first - warmup_bars):]
        score_from = OOS_START
    df = df.reset_index(drop=True)
    df.attrs.update(symbol=symbol, tf=tf, split=split, score_from=score_from)
    return df


def _attach_conv(df, symbol, tf):
    spec = _spec().get(symbol, {})
    ccy = spec.get("profit_ccy") or ("JPY" if symbol.endswith("JPY") else "USD")
    if ccy == "USD":
        df["conv"] = 1.0
        return df
    pair, invert = {"JPY": ("USDJPY", True), "CHF": ("USDCHF", True),
                    "CAD": ("USDCAD", True), "GBP": ("GBPUSD", False),
                    "EUR": ("EURUSD", False)}[ccy]
    src = None
    for t in (tf, "H1"):
        p = DATA / f"{pair.lower()}-{t.lower()}.csv"
        if p.exists():
            src = pd.read_csv(p, usecols=["time", "close"], parse_dates=["time"])
            break
    if src is None:
        raise FileNotFoundError(f"conversion series {pair} missing")
    src = src.drop_duplicates("time").sort_values("time")
    src["conv"] = 1.0 / src["close"] if invert else src["close"]
    out = pd.merge_asof(df, src[["time", "conv"]], on="time", direction="backward")
    out["conv"] = out["conv"].bfill()
    return out


@dataclass
class Entry:
    side: str                       # "long" | "short"
    sl: float                       # stop PRICE (required)
    tp: float | None = None         # target PRICE or None
    max_hold: int | None = None     # exit at close after this many bars
    exit_hour: int | None = None    # exit at close of first later bar with this hour
    manage: Callable | None = None  # manage(df, i, pos) -> None | new_sl | "close"
    meta: dict = field(default_factory=dict)


def simulate(df: pd.DataFrame, signals, *, risk: float = 0.01,
             spread_mult: float = 1.0, allow_flip: bool = True,
             daily_block: float = SAFE_DAILY, max_lots: float = 50.0) -> dict:
    """One position at a time. Returns trades + per-bar worst-case equity."""
    sym = df.attrs.get("symbol", "")
    spec = _spec().get(sym, {})
    contract = float(spec.get("contract", 100.0 if sym == "XAUUSD" else 100000.0))
    point = float(spec.get("point", 0.01))
    vstep = float(spec.get("vol_step", 0.01)) or 0.01
    vmin = float(spec.get("vol_min", 0.01)) or 0.01
    comm = 0.0 if sym in INDICES else COMMISSION_RT
    slip = 0.1 * _pip(sym)
    floor = SPREAD_FLOOR.get(sym, 0.0)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    conv = df["conv"].to_numpy(float)
    bar_spread = df["spread"].to_numpy(float) * point if "spread" in df else np.zeros(len(df))
    times = pd.DatetimeIndex(df["time"])
    days = times.normalize().to_numpy()
    hours = times.hour.to_numpy()
    n = len(df)
    get = signals if callable(signals) else (lambda _d, i: signals[i])
    risk_usd = risk * BASELINE

    realized = 0.0
    pos = None
    trades = []
    worst_eq = np.empty(n)      # realized + worst intrabar floating
    close_eq = np.empty(n)      # realized + floating at close
    day, day_start = None, 0.0

    def pnl(price, p):
        d = (price - p["entry"]) if p["side"] == "long" else (p["entry"] - price)
        return d * contract * p["lots"] * conv_i

    def settle(price, reason, i):
        nonlocal realized, pos
        gross = pnl(price, pos)
        fee = comm * pos["lots"]
        realized += gross - fee
        trades.append(dict(entry_time=times[pos["bar"]], exit_time=times[i],
                           side=pos["side"], entry=pos["entry"], exit=price,
                           sl0=pos["sl0"], lots=pos["lots"], profit=gross - fee,
                           r=(gross - fee) / pos["risk_usd"], reason=reason,
                           bars=i - pos["bar"], **pos["meta"]))
        pos = None

    for i in range(n):
        conv_i = conv[i]
        if days[i] != day:
            day, day_start = days[i], realized
        if pos is not None:
            p = pos
            long_ = p["side"] == "long"
            # gap through stop at the open
            if (long_ and o[i] <= p["sl"]) or (not long_ and o[i] >= p["sl"]):
                settle(o[i] - slip if long_ else o[i] + slip, "gap_sl", i)
            elif (long_ and l[i] <= p["sl"]) or (not long_ and h[i] >= p["sl"]):
                settle(p["sl"] - slip if long_ else p["sl"] + slip, "sl", i)
            elif p["tp"] is not None and ((long_ and h[i] >= p["tp"]) or (not long_ and l[i] <= p["tp"])):
                settle(p["tp"], "tp", i)
            else:
                if (p["max_hold"] is not None and i - p["bar"] >= p["max_hold"]) or \
                   (p["exit_hour"] is not None and hours[i] == p["exit_hour"] and i > p["bar"]):
                    settle(c[i] - slip if long_ else c[i] + slip, "time", i)
                elif p["manage"] is not None:
                    act = p["manage"](df, i, p)
                    if act == "close":
                        settle(c[i] - slip if long_ else c[i] + slip, "manage", i)
                    elif act is not None:
                        p["sl"] = float(act)
        # mark-to-market
        if pos is not None:
            adverse = l[i] if pos["side"] == "long" else h[i]
            worst_eq[i] = realized + pnl(adverse, pos) - comm * pos["lots"]
            close_eq[i] = realized + pnl(c[i], pos) - comm * pos["lots"]
        else:
            worst_eq[i] = close_eq[i] = realized

        sig = get(df, i)
        if sig is None:
            continue
        if pos is not None and allow_flip and sig.side != pos["side"]:
            settle(c[i] - slip if pos["side"] == "long" else c[i] + slip, "flip", i)
        if pos is not None:
            continue
        if close_eq[i] - day_start <= -daily_block * BASELINE:
            continue  # daily entry block
        sp = max(floor, bar_spread[i]) * spread_mult
        entry = c[i] + sp + slip if sig.side == "long" else c[i] - sp - slip
        if sig.side == "long":
            ok = sig.sl < c[i] and (sig.tp is None or sig.tp > entry)
        else:
            ok = sig.sl > c[i] and (sig.tp is None or sig.tp < entry)
        if not ok or not math.isfinite(sig.sl):
            continue
        loss_per_lot = (abs(entry - sig.sl) + slip) * contract * conv_i + comm
        if loss_per_lot <= 0:
            continue
        lots = math.floor(risk_usd / loss_per_lot / vstep) * vstep
        lots = min(round(lots, 2), max_lots)
        if lots < vmin:
            continue
        pos = dict(side=sig.side, entry=entry, sl=float(sig.sl), sl0=float(sig.sl),
                   tp=sig.tp, lots=lots, bar=i, max_hold=sig.max_hold,
                   exit_hour=sig.exit_hour, manage=sig.manage,
                   risk_usd=lots * loss_per_lot, meta=dict(sig.meta))
    if pos is not None:
        conv_i = conv[-1]
        settle(c[-1], "end", n - 1)
        worst_eq[-1] = close_eq[-1] = realized
    t = pd.DataFrame(trades)
    curve = pd.DataFrame({"time": times, "worst": worst_eq, "close": close_eq})
    return dict(trades=t, curve=curve)


def _metrics(curve: pd.DataFrame, trades: pd.DataFrame, start=None) -> dict:
    if start is not None:
        base = curve.loc[curve.time < start, "close"]
        off = float(base.iloc[-1]) if len(base) else 0.0
        curve = curve[curve.time >= start].copy()
        curve[["worst", "close"]] -= off
        if len(trades):
            trades = trades[trades.entry_time >= start]
    if curve.empty:
        return dict(trades=0, net=0.0)
    w, cl = curve["worst"].to_numpy(), curve["close"].to_numpy()
    peak = np.maximum.accumulate(np.r_[0.0, cl])[1:]
    max_dd = float((w - peak).min())
    d = curve.assign(day=curve.time.dt.normalize())
    day_open = d.groupby("day")["close"].first()
    prev_close = d.groupby("day")["close"].last().shift().fillna(0.0)
    day_low = d.groupby("day")["worst"].min()
    worst_day = float((day_low - prev_close).min())
    month_end = d.groupby(d.time.dt.to_period("M"))["close"].last()
    monthly = month_end.diff()
    monthly.iloc[0] = month_end.iloc[0]
    n_months = max(len(monthly), 1)
    net = float(cl[-1])
    out = dict(
        trades=int(len(trades)),
        win_rate=float((trades.profit > 0).mean()) if len(trades) else 0.0,
        net=net, avg_month=net / n_months,
        green_months=float((monthly > 0).mean()), worst_month=float(monthly.min()),
        months=n_months, max_dd=max_dd, worst_day=worst_day,
        firm_breach=bool(worst_day <= -FIRM_DAILY * BASELINE or max_dd <= -FIRM_TOTAL * BASELINE),
        safe=bool(worst_day > -SAFE_DAILY * BASELINE and max_dd > -SAFE_DD * BASELINE),
        monthly={str(k): round(float(v), 2) for k, v in monthly.items()},
    )
    out.update(_challenges(curve))
    return out


def _challenges(curve: pd.DataFrame, every_days: int = 14) -> dict:
    """Rolling FundedNext Stellar Lite attempts: start every `every_days`,
    phase 1 needs +8% before a breach, then phase 2 (fresh) needs +4%.
    Breach = equity (worst intrabar) below day-start balance - 4% or below
    -8% of start. Returns pass rate and median calendar days to pass both."""
    t = curve.time.to_numpy()
    w, cl = curve.worst.to_numpy(), curve.close.to_numpy()
    days = curve.time.dt.normalize().to_numpy()
    starts = pd.date_range(curve.time.iloc[0], curve.time.iloc[-1] - pd.Timedelta(days=60),
                           freq=f"{every_days}D")
    passed, failed, open_, dur = 0, 0, 0, []
    n = len(cl)
    # day-start balance for every bar = close of the bar before the day's first bar
    new_day = np.r_[True, days[1:] != days[:-1]]
    first_idx = np.maximum.accumulate(np.where(new_day, np.arange(n), 0))
    prev_cl = np.r_[0.0, cl[:-1]]
    day_start = prev_cl[first_idx]
    daily_fail = (w - day_start) <= -FIRM_DAILY * BASELINE   # independent of attempt base

    def first(mask):
        k = int(np.argmax(mask))
        return k if mask.size and mask[k] else None

    def phase(i0, target):
        base = prev_cl[i0]
        seg_fail = daily_fail[i0:].copy()
        # a day that STARTED before the attempt: measure from the attempt start instead
        same_day = days[i0:] == days[i0]
        seg_fail[same_day] = (w[i0:][same_day] - base) <= -FIRM_DAILY * BASELINE
        seg_fail |= (w[i0:] - base) <= -FIRM_TOTAL * BASELINE
        f = first(seg_fail)
        p = first((cl[i0:] - base) >= target * BASELINE)
        if f is not None and (p is None or f <= p):
            return "fail", i0 + f
        if p is not None:
            return "pass", i0 + p
        return "open", n - 1

    for s in starts:
        i0 = int(np.searchsorted(t, s.to_datetime64()))
        r1, i1 = phase(i0, PHASE_TARGETS[0])
        if r1 != "pass":
            failed += r1 == "fail"; open_ += r1 == "open"; continue
        r2, i2 = phase(i1 + 1, PHASE_TARGETS[1]) if i1 + 1 < len(cl) else ("open", i1)
        if r2 == "pass":
            passed += 1
            dur.append((t[i2] - t[i0]) / np.timedelta64(1, "D"))
        else:
            failed += r2 == "fail"; open_ += r2 == "open"
    tot = passed + failed
    return dict(challenge_attempts=len(starts), challenge_pass=passed,
                challenge_fail=failed, challenge_unfinished=open_,
                challenge_pass_rate=passed / tot if tot else 0.0,
                challenge_median_days=float(np.median(dur)) if dur else None)


def score(df: pd.DataFrame, signals, *, risks=RISKS, spread_mult: float = 1.0,
          allow_flip: bool = True, name: str = "") -> dict:
    """Run at each risk level; best_risk = highest risk that stays SAFE
    (worst day > -3%, max DD > -6%). Headline = metrics at best_risk."""
    start = df.attrs.get("score_from")
    rows = {}
    for r in risks:
        res = simulate(df, signals, risk=r, spread_mult=spread_mult, allow_flip=allow_flip)
        rows[r] = (_metrics(res["curve"], res["trades"], start), res["trades"])
    safe = [r for r in risks if rows[r][0].get("safe")]
    best = max(safe) if safe else None
    head = rows[best][0] if best is not None else rows[min(risks)][0]
    return dict(name=name, symbol=df.attrs.get("symbol"), tf=df.attrs.get("tf"),
                split=df.attrs.get("split"), spread_mult=spread_mult,
                best_risk=best, headline=head,
                by_risk={str(r): {k: v for k, v in m.items() if k != "monthly"}
                         for r, (m, _) in rows.items()},
                trades_at_best=rows[best][1] if best is not None else None)


def summary_line(s: dict) -> str:
    h = s["headline"]
    br = f"{s['best_risk']*100:.2f}%" if s["best_risk"] else "NONE-SAFE"
    return (f"{s['name']:<40} {s['symbol']:<7}{s['tf']:<4} risk {br:<9} "
            f"net ${h.get('net', 0):>9,.0f}  avg/mo ${h.get('avg_month', 0):>7,.0f}  "
            f"green {h.get('green_months', 0)*100:>3.0f}%  maxDD ${h.get('max_dd', 0):>7,.0f}  "
            f"worstDay ${h.get('worst_day', 0):>6,.0f}  trades {h.get('trades', 0):>5}  "
            f"chal {h.get('challenge_pass_rate', 0)*100:>3.0f}% "
            f"({h.get('challenge_median_days')} d)")
