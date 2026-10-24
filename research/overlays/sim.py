"""Exact per-strategy simulation for the overlay lab.

`simulate` is a copy of research.prop.harness.simulate with ONE addition: an
optional minimum stop distance used for SIZING only,

    size_dist = max(|entry - stop|, min_stop_k * ADR20(symbol))

where ADR20 is the average (high - low) of the previous 20 server days. The
real stop is untouched; only the lot count shrinks when a strategy's stop is
abnormally tight (the DAX 9.9-point stop that got 11.8 lots on 2024-11-29).
Every trade records `stop_dist`, `size_dist` and `resized`.

`run_strategy` reproduces portfolio_2yr.run from the sizing session: load the
symbol with 6000 bars of warm-up, build the strategy's signals once, blank the
signals before the window start (start flat) and simulate at the live risk,
once per min_stop_k requested (k=0 is the plain harness result).
"""
from __future__ import annotations

import importlib
import math
import os

import numpy as np
import pandas as pd

os.environ.setdefault("PROP_OOS", "1")
from research.prop import harness as H  # noqa: E402

WARM = 6000
ADR_DAYS = 20


def adr20(df: pd.DataFrame, days: int = ADR_DAYS) -> np.ndarray:
    """Per bar: mean (high-low) of the previous `days` completed server days."""
    t = pd.DatetimeIndex(df["time"]).normalize()
    g = pd.DataFrame({"d": t, "h": df["high"].to_numpy(float), "l": df["low"].to_numpy(float)})
    rng = g.groupby("d").agg(h=("h", "max"), l=("l", "min"))
    rng = (rng["h"] - rng["l"]).rolling(days, min_periods=max(5, days // 2)).mean().shift(1)
    return rng.reindex(t).to_numpy(float)


def simulate(df: pd.DataFrame, signals, *, risk: float = 0.01, spread_mult: float = 1.0,
             allow_flip: bool = True, daily_block: float = H.SAFE_DAILY,
             max_lots: float = 50.0, min_stop_k: float = 0.0) -> dict:
    """harness.simulate + min_stop_k (0 = identical to the harness)."""
    sym = df.attrs.get("symbol", "")
    spec = H._spec().get(sym, {})
    contract = float(spec.get("contract", 100.0 if sym == "XAUUSD" else 100000.0))
    point = float(spec.get("point", 0.01))
    vstep = float(spec.get("vol_step", 0.01)) or 0.01
    vmin = float(spec.get("vol_min", 0.01)) or 0.01
    comm = 0.0 if sym in H.INDICES else H.COMMISSION_RT
    slip = 0.1 * H._pip(sym)
    floor = H.SPREAD_FLOOR.get(sym, 0.0)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    conv = df["conv"].to_numpy(float)
    bar_spread = df["spread"].to_numpy(float) * point if "spread" in df else np.zeros(len(df))
    times = pd.DatetimeIndex(df["time"])
    days = times.normalize().to_numpy()
    hours = times.hour.to_numpy()
    n = len(df)
    get = signals if callable(signals) else (lambda _d, i: signals[i])
    risk_usd = risk * H.BASELINE
    adr = adr20(df) if min_stop_k > 0 else None

    realized = 0.0
    pos = None
    trades = []
    worst_eq = np.empty(n)
    close_eq = np.empty(n)
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
                           bars=i - pos["bar"], stop_dist=pos["stop_dist"],
                           size_dist=pos["size_dist"], resized=pos["resized"],
                           **pos["meta"]))
        pos = None

    for i in range(n):
        conv_i = conv[i]
        if days[i] != day:
            day, day_start = days[i], realized
        if pos is not None:
            p = pos
            long_ = p["side"] == "long"
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
        if close_eq[i] - day_start <= -daily_block * H.BASELINE:
            continue
        sp = max(floor, bar_spread[i]) * spread_mult
        entry = c[i] + sp + slip if sig.side == "long" else c[i] - sp - slip
        if sig.side == "long":
            ok = sig.sl < c[i] and (sig.tp is None or sig.tp > entry)
        else:
            ok = sig.sl > c[i] and (sig.tp is None or sig.tp < entry)
        if not ok or not math.isfinite(sig.sl):
            continue
        stop_dist = abs(entry - sig.sl)
        size_dist = stop_dist
        resized = False
        if adr is not None and np.isfinite(adr[i]) and min_stop_k * adr[i] > stop_dist:
            size_dist = min_stop_k * adr[i]
            resized = True
        loss_per_lot = (size_dist + slip) * contract * conv_i + comm
        if loss_per_lot <= 0:
            continue
        lots = math.floor(risk_usd / loss_per_lot / vstep) * vstep
        lots = min(round(lots, 2), max_lots)
        if lots < vmin:
            continue
        true_loss_per_lot = (stop_dist + slip) * contract * conv_i + comm
        pos = dict(side=sig.side, entry=entry, sl=float(sig.sl), sl0=float(sig.sl),
                   tp=sig.tp, lots=lots, bar=i, max_hold=sig.max_hold,
                   exit_hour=sig.exit_hour, manage=sig.manage,
                   risk_usd=lots * true_loss_per_lot, meta=dict(sig.meta),
                   stop_dist=stop_dist, size_dist=size_dist, resized=resized)
    if pos is not None:
        conv_i = conv[-1]
        settle(c[-1], "end", n - 1)
        worst_eq[-1] = close_eq[-1] = realized
    t = pd.DataFrame(trades)
    curve = pd.DataFrame({"time": times, "worst": worst_eq, "close": close_eq})
    return dict(trades=t, curve=curve)


def _call(fn, df, params):
    try:
        return fn(df, **params)
    except TypeError:
        return fn(df, **{k: tuple(v) if isinstance(v, list) else v for k, v in params.items()})


def prep(x: dict, start: pd.Timestamp, end: pd.Timestamp):
    """Bars (with warm-up) and signals for strategy x, flat before `start`."""
    full = H.load(x["symbol"], x["tf"], split="all")
    full = full[full.time < end].reset_index(drop=True)
    i0 = int(np.searchsorted(full.time.values, start.to_datetime64()))
    df = full.iloc[max(0, i0 - WARM):].reset_index(drop=True)
    df.attrs.update(symbol=x["symbol"], tf=x["tf"], split="all", score_from=None)
    j0 = int(np.searchsorted(df.time.values, start.to_datetime64()))
    fn = getattr(importlib.import_module(x["module"]), x["fn"])
    sigs = list(_call(fn, df, x["params"]))
    sigs[:j0] = [None] * j0
    return df, sigs


TRADE_COLS = ("entry_time", "exit_time", "side", "entry", "exit", "sl0", "lots", "profit", "r",
              "reason", "bars", "stop_dist", "size_dist", "resized")


def run_strategy(x: dict, risk: float, start: pd.Timestamp, end: pd.Timestamp,
                 ks=(0.0,)) -> dict:
    """{k: (curve from start, trades from start)} for each min_stop_k in ks."""
    df, sigs = prep(x, start, end)
    out = {}
    for k in ks:
        res = simulate(df, sigs, risk=risk, min_stop_k=k)
        cv = res["curve"]
        cv = cv[cv.time >= start].reset_index(drop=True)
        cv["worst"] = cv["worst"].astype(np.float32)
        cv["close"] = cv["close"].astype(np.float32)
        t = res["trades"]
        if len(t):
            t = t[t.entry_time >= start].reset_index(drop=True)
            t = t[[c for c in TRADE_COLS if c in t]]
        out[k] = (cv, t)
    return out
