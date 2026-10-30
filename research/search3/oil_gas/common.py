"""Shared plumbing for the oil_gas group: cost patches, data-quality filter,
look-ahead check and a result logger. Research code only."""
from __future__ import annotations
import os, json, random, time
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H

SYMS = ("XTIUSD", "XBRUSD", "XNGUSD")
# IC Markets / FundedNext typical energy CFD spreads, price units (conservative)
H.SPREAD_FLOOR.update({"XTIUSD": 0.04, "XBRUSD": 0.04, "XNGUSD": 0.010,
                       "USOUSD": 0.04, "UKOUSD": 0.04})
H.INDICES.update({"XTIUSD", "XBRUSD", "XNGUSD", "USOUSD", "UKOUSD"})   # no $14/lot commission on energies
_orig_pip = H._pip
def _pip(symbol):
    if symbol in ("XTIUSD", "XBRUSD", "USOUSD", "UKOUSD"):
        return 0.01
    if symbol == "XNGUSD":
        return 0.001
    return _orig_pip(symbol)
H._pip = _pip


def clean(df: pd.DataFrame, report: dict | None = None) -> pd.DataFrame:
    """Drop zero-volume bars and bars on flat/stale days (daily range < 5% of
    the median daily range). Records counts in `report`."""
    attrs = dict(df.attrs)
    n0 = len(df)
    zero = (df.tick_volume <= 0) if "tick_volume" in df else pd.Series(False, index=df.index)
    day = df.time.dt.normalize()
    rng = (df.high - df.low).groupby(day).transform("sum") if attrs.get("tf", "").upper() != "D1" else (df.high - df.low)
    drng = (df.groupby(day).high.max() - df.groupby(day).low.min())
    med = drng.median()
    flat_days = set(drng[drng < 0.05 * med].index)
    flat = day.isin(flat_days)
    gaps = df.time.diff()
    long_gap = int((gaps > pd.Timedelta(days=3, hours=12)).sum())
    out = df[~(zero | flat)].reset_index(drop=True)
    out.attrs.update(attrs)
    if report is not None:
        report.update(bars=n0, zero_volume=int(zero.sum()), flat_days=len(flat_days),
                      flat_bars=int(flat.sum()), long_gaps=long_gap, kept=len(out))
    return out


_cache = {}
def load(sym, tf):
    key = (sym, tf)
    if key not in _cache:
        rep = {}
        df = clean(H.load(sym, tf, split="oos"), rep)
        _cache[key] = (df, rep)
    return _cache[key]


def causal_ok(build, df, params, k_list=None, seed=0):
    """Look-ahead check: build on the full df vs. on df.iloc[:k]; every Entry at
    index < k must match (side, sl, tp, max_hold, exit_hour)."""
    full = build(df, **params)
    rnd = random.Random(seed)
    n = len(df)
    ks = k_list or [rnd.randint(int(n * 0.3), n - 5) for _ in range(5)]
    def key(e):
        return None if e is None else (e.side, round(float(e.sl), 6),
                                       None if e.tp is None else round(float(e.tp), 6),
                                       e.max_hold, e.exit_hour)
    for k in ks:
        part = df.iloc[:k].copy()
        part.attrs.update(df.attrs)
        sub = build(part, **params)
        if len(sub) != k:
            return False, f"len {len(sub)} != {k}"
        for i in range(k):
            if key(full[i]) != key(sub[i]):
                return False, f"mismatch at i={i} (k={k}): {key(full[i])} vs {key(sub[i])}"
    return True, "ok"


RESULTS = os.path.join(os.path.dirname(__file__), "runs.jsonl")
def log_run(name, sym, tf, fn, params, s):
    h = s["headline"]
    row = dict(name=name, symbol=sym, tf=tf, build_fn=fn, params=params,
               best_risk=s["best_risk"], avg_month=round(h.get("avg_month", 0), 1),
               net=round(h.get("net", 0), 0), max_dd=round(h.get("max_dd", 0), 0),
               worst_day=round(h.get("worst_day", 0), 0), green=round(h.get("green_months", 0), 2),
               trades=h.get("trades", 0), win=round(h.get("win_rate", 0), 2),
               chal=round(h.get("challenge_pass_rate", 0), 2), ts=time.time())
    with open(RESULTS, "ab", buffering=0) as f:      # one unbuffered write per row: safe with two appenders
        f.write((json.dumps(row) + "\n").encode())
    return row


def run(df, build, fn_name, name, **params):
    sigs = build(df, **params)
    s = H.score(df, sigs, name=name)
    row = log_run(name, df.attrs["symbol"], df.attrs["tf"], fn_name, params, s)
    br = f"{row['best_risk']*100:.2f}%" if row["best_risk"] else "NONE"
    print(f"{name:<38}{row['symbol']:<8}{row['tf']:<4} risk {br:<6} avg/mo {row['avg_month']:>7.0f} "
          f"net {row['net']:>7.0f} dd {row['max_dd']:>6.0f} wd {row['worst_day']:>5.0f} "
          f"tr {row['trades']:>4} win {row['win']:.2f} green {row['green']:.2f}", flush=True)
    return row
