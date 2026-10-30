"""Batch runner for the commodity_fx group (round 3).

    python -m research.search3.commodity_fx.run [batch ...]   (default: all)

Scores every (idea, params, symbol, tf) on split='oos' (2024-10-20..now)
and appends one JSON line per run to results.jsonl. Pool(2) at most.
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ["PROP_OOS"] = "1"

import numpy as np
import pandas as pd

from research.prop import harness as H

OUT = Path(__file__).with_name("results.jsonl")

# --------------------------------------------------------------- patches
# Cross spread floors in PRICE units (IC Markets raw-ish, conservative).
EXTRA_FLOOR = {
    "EURAUD": 0.00025, "GBPAUD": 0.00035, "AUDNZD": 0.00025, "EURNZD": 0.00040,
    "GBPNZD": 0.00050, "EURCAD": 0.00025, "GBPCAD": 0.00035, "AUDCHF": 0.00025,
    "CADCHF": 0.00025, "NZDCAD": 0.00030, "NZDCHF": 0.00030,
}
EXTRA_SPEC = {   # symbols missing from data/search/symbol_specs.json
    "GBPCAD": dict(digits=5, point=1e-5, contract=100000.0, profit_ccy="CAD", vol_min=0.01, vol_step=0.01),
    "AUDCHF": dict(digits=5, point=1e-5, contract=100000.0, profit_ccy="CHF", vol_min=0.01, vol_step=0.01),
    "CADCHF": dict(digits=5, point=1e-5, contract=100000.0, profit_ccy="CHF", vol_min=0.01, vol_step=0.01),
    "NZDCAD": dict(digits=5, point=1e-5, contract=100000.0, profit_ccy="CAD", vol_min=0.01, vol_step=0.01),
    "NZDCHF": dict(digits=5, point=1e-5, contract=100000.0, profit_ccy="CHF", vol_min=0.01, vol_step=0.01),
}
CONV = {"JPY": ("USDJPY", True), "CHF": ("USDCHF", True), "CAD": ("USDCAD", True),
        "GBP": ("GBPUSD", False), "EUR": ("EURUSD", False),
        "AUD": ("AUDUSD", False), "NZD": ("NZDUSD", False)}


def patch():
    H.SPREAD_FLOOR.update(EXTRA_FLOOR)
    _orig_spec = H._spec

    def _spec():
        d = dict(_orig_spec())
        for k, v in EXTRA_SPEC.items():
            d.setdefault(k, v)
        return d
    H._spec = _spec

    def _attach_conv(df, symbol, tf):
        spec = H._spec().get(symbol, {})
        ccy = spec.get("profit_ccy") or ("JPY" if symbol.endswith("JPY") else "USD")
        if ccy == "USD":
            df["conv"] = 1.0
            return df
        pair, invert = CONV[ccy]
        src = None
        for t in (tf, "H1"):
            p = H.DATA / f"{pair.lower()}-{t.lower()}.csv"
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
    H._attach_conv = _attach_conv


patch()

# Data quality: drop bars on "flat" days (daily range < 5% of the median).
def clean(df):
    t = pd.DatetimeIndex(df.time)
    day = t.normalize()
    rng = pd.DataFrame({"d": day, "r": df.high.values - df.low.values}).groupby("d").r.agg(lambda x: x.max() if len(x) else 0)
    rng = (df.assign(d=day).groupby("d").high.max() - df.assign(d=day).groupby("d").low.min())
    bad = rng[rng < 0.05 * rng.median()].index
    keep = ~day.isin(bad) & (df.tick_volume.values > 0)
    attrs = dict(df.attrs)
    out = df[keep].reset_index(drop=True)
    out.attrs.update(attrs)
    out.attrs["dropped_bars"] = int((~keep).sum())
    return out


_cache = {}


def load(sym, tf):
    k = (sym, tf)
    if k not in _cache:
        if len(_cache) > 4:
            _cache.clear()
        _cache[k] = clean(H.load(sym, tf, split="oos"))
    return _cache[k]


def exit_type(fn, params):
    if fn in ("asia_break", "asia_fade", "weekday", "monday_gap", "london_rev", "asia_drift"):
        return "tp+session_time" if fn != "weekday" and fn != "asia_drift" else "session_time"
    if fn in ("donchian", "zmean", "rsi2"):
        return "manage_trail/close+sl"
    if fn in ("squeeze", "trend_pullback") and params.get("trail_atr"):
        return "chandelier+sl"
    return "tp+sl+max_hold"


def run_one(job):
    name, fn, sym, tf, params, batch = job
    from research.search3.commodity_fx import strategies as S
    try:
        df = load(sym, tf)
        sigs = getattr(S, "build_" + fn)(df, **params)
        s = H.score(df, sigs, name=name)
        h = s["headline"]
        row = dict(batch=batch, name=name, build_fn=fn, symbol=sym, tf=tf, params=params,
                   best_risk=s["best_risk"], exit_type=exit_type(fn, params),
                   n_signals=int(sum(x is not None for x in sigs)),
                   **{k: h.get(k) for k in ("net", "avg_month", "green_months", "max_dd",
                                            "worst_day", "trades", "challenge_pass_rate", "win_rate")})
        return row, H.summary_line(s)
    except Exception as e:
        return dict(batch=batch, name=name, build_fn=fn, symbol=sym, tf=tf, params=params,
                    error=repr(e)), f"ERR {name} {sym} {tf} {e!r}"


# --------------------------------------------------------------- batches
ALL = ["AUDUSD", "NZDUSD", "USDCAD", "EURAUD", "GBPAUD", "AUDNZD", "EURNZD", "GBPNZD",
       "EURCAD", "GBPCAD", "AUDCHF", "CADCHF", "NZDCAD", "NZDCHF"]
CROSSES = [s for s in ALL if s not in ("AUDUSD", "NZDUSD", "USDCAD")]
RANGERS = ["AUDNZD", "AUDCHF", "NZDCHF", "NZDCAD", "CADCHF", "EURCAD"]


def avail(syms, tf):
    return [s for s in syms if (H.DATA / f"{s.lower()}-{tf.lower()}.csv").exists()]


def jobs():
    J = []

    def add(batch, fn, syms, tf, grid):
        for s in avail(syms, tf):
            for p in grid:
                tag = "_".join(f"{k}{v}" for k, v in p.items())
                J.append((f"{fn}_{tag}", fn, s, tf, p, batch))

    # 1 asia break (H1)
    add("asia", "asia_break", ALL, "H1", [
        dict(tp_r=1.5), dict(tp_r=1.0, sl_mode="atr", sl_atr=1.0), dict(tp_r=2.0, max_r=1.0),
        dict(tp_r=1.5, last_hour=12, exit_hour=18)])
    # 2 asia fade (H1)
    add("asia", "asia_fade", ALL, "H1", [
        dict(), dict(tp_mode="r", tp_r=1.0), dict(pen_atr=0.15, sl_atr=0.5), dict(last_hour=12)])
    # 3 pd sweep (H1)
    add("levels", "pd_sweep", ALL, "H1", [
        dict(), dict(tp_mode="r", tp_r=1.5), dict(pen_atr=0.2, sl_atr=0.4, tp_mode="r", tp_r=1.0),
        dict(hours=(10, 18), max_hold=8)])
    # 4 pd break (H1)
    add("levels", "pd_break", ALL, "H1", [
        dict(), dict(sl_mode="atr", sl_atr=1.0, tp_r=2.0), dict(tp_r=1.0, max_hold=6)])
    # 5 d1 meanrev (D1 + H4)
    add("meanrev", "d1_meanrev", ALL, "D1", [
        dict(z_thr=1.5), dict(z_thr=2.0, max_hold=2), dict(z_thr=1.5, need_streak=3),
        dict(z_thr=1.0, need_streak=3, tp_r=1.5, max_hold=5)])
    add("meanrev", "d1_meanrev", ALL, "H4", [dict(z_thr=2.0, max_hold=2), dict(z_thr=1.5, need_streak=0)])
    # 6 trend pullback (D1 + H4)
    add("trend", "trend_pullback", ALL, "D1", [
        dict(), dict(tp_r=3.0, max_hold=25), dict(trail_atr=3.0, max_hold=40, tp_r=None),
        dict(fast=10, slow=30, bias=100, tp_r=2.0)])
    add("trend", "trend_pullback", ALL, "H4", [
        dict(), dict(trail_atr=3.0, max_hold=60, tp_r=None), dict(fast=10, slow=30, bias=100, tp_r=2.0, max_hold=30)])
    # 7 BB reentry (H1 + H4)
    add("range", "bb_reentry", ALL, "H4", [
        dict(), dict(adx_max=25), dict(rsi_thr=40, k=2.5), dict(tp_mode="r", sl_atr=0.8)])
    add("range", "bb_reentry", ALL, "H1", [dict(), dict(adx_max=25, k=2.5)])
    # 8 weekday
    add("calendar", "weekday", ALL, "H1", [
        dict(), dict(long_days=(0,), short_days=(), tp_atr=None), dict(long_days=(), short_days=(4,)),
        dict(entry_hour=9, exit_hour=22), dict(sl_atr=1.0, tp_atr=1.5)])
    # 9 monday gap
    add("calendar", "monday_gap", ALL, "H1", [dict(), dict(min_gap_atr=0.3), dict(min_gap_atr=0.15, sl_mult=2.5, exit_hour=12)])
    # 10 gold div (AUD/NZD vs gold; CAD vs gold too)
    add("corr", "gold_div", ["AUDUSD", "NZDUSD", "USDCAD", "AUDNZD", "AUDCHF", "NZDCHF"], "H1", [
        dict(), dict(mode="fade"), dict(n=24, z_n=240, z_thr=1.5, max_hold=24), dict(n=24, z_n=240, z_thr=1.5, max_hold=24, mode="fade")])
    add("corr", "gold_div", ["AUDUSD", "NZDUSD", "USDCAD", "AUDNZD", "AUDCHF", "NZDCHF"], "D1", [
        dict(), dict(mode="fade"), dict(n=10, z_n=120, z_thr=1.5, max_hold=10)])
    # 11 london reversal
    add("session", "london_rev", ALL, "H1", [dict(), dict(move_atr=1.2, tp_mode="r", tp_r=1.5), dict(at_hour=12, move_atr=1.0, exit_hour=20)])
    # 12 squeeze (H4 + D1)
    add("vol", "squeeze", ALL, "H4", [dict(), dict(tp_r=2.0, trail_atr=None, max_hold=40), dict(pct=0.1, trail_atr=2.0)])
    add("vol", "squeeze", ALL, "D1", [dict(pct_n=60, max_hold=30), dict(pct_n=60, tp_r=2.0, trail_atr=None, max_hold=20)])
    # 13 round numbers
    add("levels", "round_bounce", ALL, "H1", [dict(), dict(step=0.01, tp_r=2.0), dict(step=0.0025, wick_ratio=2.0, tp_r=1.0)])
    # 14 week fade (H1 + H4)
    add("levels", "week_fade", ALL, "H4", [dict(), dict(adx_max=20, tp_mode="r", tp_r=1.5), dict(adx_max=30, sl_atr=1.0)])
    add("levels", "week_fade", ALL, "H1", [dict(max_hold=48), dict(adx_max=20, tp_mode="r", tp_r=1.5, max_hold=48)])
    # 15 donchian (D1 + H4)
    add("trend", "donchian", ALL, "D1", [dict(), dict(n_in=55, n_out=20), dict(n_in=20, n_out=10, adx_min=20), dict(n_in=10, n_out=5)])
    add("trend", "donchian", ALL, "H4", [dict(n_in=50, n_out=20), dict(n_in=120, n_out=40, sl_atr=3.0)])
    # 16 rsi2 (D1 + H4)
    add("meanrev", "rsi2", ALL, "D1", [dict(), dict(rsi_thr=5), dict(rsi_thr=15, exit_ma=3), dict(rsi_thr=10, both=False)])
    add("meanrev", "rsi2", ALL, "H4", [dict(rsi_thr=5, ma_n=200, exit_ma=5, max_hold=20), dict(rsi_thr=10, ma_n=100, exit_ma=3, max_hold=20)])
    # 17 inside/NR7 (D1)
    add("vol", "inside_break", ALL, "D1", [dict(), dict(mode="nr", nr_n=7), dict(mode="nr", nr_n=4, tp_r=1.0, max_hold=2), dict(trend_n=50, tp_r=2.0)])
    # 18 z-score to mean (H4 + H1 + D1)
    add("range", "zmean", ALL, "H4", [dict(), dict(n=50, z_in=2.0, sl_atr=1.5, max_hold=50), dict(n=200, z_in=2.5, sl_atr=2.5, max_hold=200), dict(n=100, adx_max=25)])
    add("range", "zmean", ALL, "H1", [dict(n=240, z_in=2.5, sl_atr=2.5, max_hold=240), dict(n=120, z_in=2.0, sl_atr=2.0, max_hold=120, adx_max=25)])
    add("range", "zmean", ALL, "D1", [dict(n=20, z_in=2.0, sl_atr=2.0, max_hold=20), dict(n=50, z_in=2.0, sl_atr=2.5, max_hold=40)])
    # 19 asia drift
    add("session", "asia_drift", ALL, "H1", [dict(), dict(mode="fade"), dict(lookback_days=20), dict(entry_hour=2, exit_hour=8, lookback_days=5)])
    # 20 pdc magnet
    add("levels", "pdc_magnet", ALL, "H1", [dict(), dict(dist_atr=0.4, hours=(9, 20)), dict(dist_atr=0.8, sl_atr=1.2, max_hold=16)])
    return J


def main(argv):
    only = set(argv) if argv else None
    J = [j for j in jobs() if only is None or j[5] in only or j[1] in only]
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                r = json.loads(line)
                done.add((r["name"], r["symbol"], r["tf"]))
            except Exception:
                pass
    J = [j for j in J if (j[0], j[2], j[3]) not in done]
    # group by symbol/tf so each worker's cache is hit
    J.sort(key=lambda j: (j[2], j[3], j[1]))
    print(f"{len(J)} jobs to run", flush=True)
    t0 = time.time()
    with Pool(2) as pool, OUT.open("a") as f:
        for k, (row, line) in enumerate(pool.imap(run_one, J, chunksize=4)):
            f.write(json.dumps(row) + "\n"); f.flush()
            if k % 10 == 0 or row.get("avg_month", 0) and row.get("best_risk"):
                print(f"[{k+1}/{len(J)} {time.time()-t0:.0f}s] {line}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
