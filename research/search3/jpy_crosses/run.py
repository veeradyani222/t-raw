"""Batch runner for research/search3/jpy_crosses (round 3, scoring window
2024-10-20..now, PROP_OOS=1). Pool(2) at most (RAM). Every scored run is
appended to results.jsonl; every run also passes the look-ahead check
(build(df) vs build(df.iloc[:k]) for 5 random k) before scoring.

    python -m research.search3.jpy_crosses.run <batch> [<batch> ...]
    python -m research.search3.jpy_crosses.run smoke
"""
from __future__ import annotations

import os
os.environ["PROP_OOS"] = "1"

import gc
import json
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from research.prop import harness as H
from research.search3.jpy_crosses import strategies as S

HERE = Path(__file__).resolve().parent
LOG = HERE / "results.jsonl"
JPY = S.ALL_JPY
_cache = {}


def load(sym, tf):
    k = (sym, tf)
    if k not in _cache:
        if len(_cache) >= 2:
            _cache.clear(); gc.collect()
        _cache[k] = H.load(sym, tf, split="oos")
    return _cache[k]


def _sig_key(e):
    if e is None:
        return None
    return (e.side, round(e.sl, 6), None if e.tp is None else round(e.tp, 6), e.max_hold, e.exit_hour,
            e.manage is not None, json.dumps(e.meta, sort_keys=True, default=str))


def causal_check(fn, df, params, n=5, seed=0):
    """build(df) vs build(df.iloc[:k]): every Entry at index < k must match."""
    full = fn(df, **params)
    rng = random.Random(seed)
    lo = max(200, int(len(df) * 0.4))
    for k in [rng.randint(lo, len(df) - 2) for _ in range(n)]:
        part = df.iloc[:k].copy()
        part.attrs.update(df.attrs)
        sub = fn(part, **params)
        if len(sub) != k:
            return False, f"len {len(sub)} != {k}"
        for i in range(k):
            if _sig_key(full[i]) != _sig_key(sub[i]):
                return False, f"k={k} i={i} full={_sig_key(full[i])} part={_sig_key(sub[i])}"
    return True, "ok"


def run_one(job):
    name, sym, tf, fn, params, batch = job
    df = None
    for attempt in range(8):          # RAM is tight: retry a failed CSV parse
        try:
            df = load(sym, tf)
            break
        except (MemoryError, Exception) as e:   # pandas raises ParserError on OOM
            if attempt == 7:
                raise
            _cache.clear(); gc.collect(); time.sleep(20)
    f = getattr(S, fn)
    t0 = time.time()
    ok, msg = causal_check(f, df, params)
    sigs = f(df, **params)
    s = H.score(df, sigs, name=name)
    h = s["headline"]
    row = dict(batch=batch, name=name, symbol=sym, tf=tf, fn=fn, params=params,
               best_risk=s["best_risk"], net=h.get("net"), avg_month=h.get("avg_month"),
               green=h.get("green_months"), max_dd=h.get("max_dd"),
               worst_day=h.get("worst_day"), trades=h.get("trades"),
               win=h.get("win_rate"), chal=h.get("challenge_pass_rate"),
               r025=s["by_risk"]["0.0025"].get("net"), n_sigs=int(sum(x is not None for x in sigs)),
               causal_ok=ok, causal_msg=msg, secs=round(time.time() - t0, 1))
    return row, H.summary_line(s)


def _done():
    out = set()
    if LOG.exists():
        for l in LOG.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                out.add((r["name"], r["symbol"], r["tf"]))
    return out


def run_jobs(jobs, procs=2):
    done = _done()
    jobs = [j for j in jobs if (j[0], j[1], j[2]) not in done]
    print(f"   {len(jobs)} jobs left after resume", flush=True)
    if not jobs:
        return
    if procs <= 1:
        it = map(run_one, jobs)
    else:
        pool = Pool(procs)
        it = pool.imap_unordered(run_one, jobs)
    with LOG.open("a") as f:
        for row, line in it:
            f.write(json.dumps(row, default=str) + "\n"); f.flush()
            flag = "" if row["causal_ok"] else f"  !! LOOKAHEAD {row['causal_msg']}"
            print(line, f"[{row['secs']}s]{flag}", flush=True)
    if procs > 1:
        pool.close(); pool.join()


BATCHES = {}


def batch(name):
    def deco(f):
        BATCHES[name] = f
        return f
    return deco


def J(batch_, name, fn, params, syms=JPY, tfs=("H1",)):
    return [(name, s, tf, fn, dict(params), batch_) for s in syms for tf in tfs]


# ------------------------------------------------------------------ batches
@batch("smoke")
def _smoke():
    g = ["GBPJPY"]
    return (J("smoke", "pdh_sweep", "build_pdh_sweep", {}, g)
            + J("smoke", "pdh_break", "build_pdh_break", {}, g)
            + J("smoke", "tokyo_sweep", "build_tokyo_sweep", {}, g)
            + J("smoke", "gap_fade", "build_gap_fade", {}, g)
            + J("smoke", "bigday_fade", "build_bigday_fade", {}, g)
            + J("smoke", "rsi2_d1", "build_rsi2", {}, g, ("D1",))
            + J("smoke", "pwh_sweep", "build_pwh_sweep", {}, g, ("H4",))
            + J("smoke", "round_number", "build_round_number", {}, g)
            + J("smoke", "nr_break", "build_nr_break", {}, g)
            + J("smoke", "donchian", "build_donchian", {}, g, ("H4",))
            + J("smoke", "ema_pullback", "build_ema_pullback", {}, g, ("H4",))
            + J("smoke", "shock_day", "build_shock_day", {}, g)
            + J("smoke", "tokyo_fix", "build_tokyo_fix", {}, ["USDJPY"])
            + J("smoke", "london_fade", "build_london_fade", {}, g)
            + J("smoke", "yen_basket", "build_yen_basket", {}, g)
            + J("smoke", "carry_dip", "build_carry_dip", {}, g, ("D1",))
            + J("smoke", "rollover", "build_rollover", {}, g)
            + J("smoke", "band_fade", "build_band_fade", {}, g, ("H4",))
            + J("smoke", "week_open_fade", "build_week_open_fade", {}, g)
            + J("smoke", "day_open_fade", "build_day_open_fade", {}, g))


@batch("b1")   # structure fades, base settings, all pairs, H1 + M30
def _b1():
    j = []
    j += J("b1", "pdh_sweep_mid", "build_pdh_sweep", dict(tp="mid"), tfs=("H1", "M30"))
    j += J("b1", "pdh_sweep_pdc", "build_pdh_sweep", dict(tp="pdc"), tfs=("H1",))
    j += J("b1", "pdh_sweep_p1", "build_pdh_sweep", dict(pierce=0.1, tp="mid"), tfs=("H1",))
    j += J("b1", "tokyo_sweep_rng", "build_tokyo_sweep", dict(tp="range"), tfs=("H1", "M30"))
    j += J("b1", "tokyo_sweep_mid", "build_tokyo_sweep", dict(tp="mid"), tfs=("H1",))
    j += J("b1", "gap_fade_fill", "build_gap_fade", dict(), tfs=("H1",))
    j += J("b1", "gap_fade_half", "build_gap_fade", dict(tp="half", min_gap=0.1), tfs=("H1",))
    j += J("b1", "day_open_fade", "build_day_open_fade", dict(), tfs=("H1",))
    j += J("b1", "day_open_fade_k1", "build_day_open_fade", dict(k=1.0, tp_frac=0.5), tfs=("H1",))
    j += J("b1", "week_open_fade", "build_week_open_fade", dict(), tfs=("H1",))
    j += J("b1", "week_open_fade_k2", "build_week_open_fade", dict(k=2.0), tfs=("H1",))
    return j


@batch("b2")   # daily-scale mean reversion executed intraday / on D1
def _b2():
    j = []
    for k in (1.0, 1.3, 1.6):
        j += J("b2", f"bigday_fade_k{k}", "build_bigday_fade", dict(k=k), tfs=("H1",))
    j += J("b2", "bigday_follow_k1.3", "build_bigday_fade", dict(k=1.3, mode="follow"), tfs=("H1",))
    j += J("b2", "bigday_fade_ldn", "build_bigday_fade", dict(k=1.2, entry_h=9.0, max_hold=14), tfs=("H1",))
    j += J("b2", "rsi2_d1_trend", "build_rsi2", dict(), tfs=("D1",))
    j += J("b2", "rsi2_d1_counter", "build_rsi2", dict(counter=True), tfs=("D1",))
    j += J("b2", "rsi2_h4_trend", "build_rsi2", dict(trend_n=200, exit_n=5, max_hold=30), tfs=("H4",))
    j += J("b2", "rsi2_h4_counter", "build_rsi2", dict(counter=True, lo=5, hi=95, max_hold=30), tfs=("H4",))
    j += J("b2", "band_fade_h4", "build_band_fade", dict(), tfs=("H4",))
    j += J("b2", "band_fade_h4_trend", "build_band_fade", dict(trend_n=200), tfs=("H4",))
    j += J("b2", "band_fade_h1_k3", "build_band_fade", dict(k=3.0, n=24), tfs=("H1",))
    j += J("b2", "shock_fade", "build_shock_day", dict(), tfs=("H1",))
    j += J("b2", "shock_follow", "build_shock_day", dict(mode="follow"), tfs=("H1",))
    j += J("b2", "shock_fade_d1", "build_shock_day", dict(k=2.0, hold_days=3), tfs=("D1",))
    j += J("b2", "yen_basket_fade", "build_yen_basket", dict(), tfs=("H1",))
    j += J("b2", "yen_basket_follow", "build_yen_basket", dict(mode="follow"), tfs=("H1",))
    j += J("b2", "yen_basket_fade_z2", "build_yen_basket", dict(z=2.0, max_hold=48), tfs=("H1",))
    return j


@batch("b3")   # breakouts / trend / pullbacks
def _b3():
    j = []
    j += J("b3", "pdh_break", "build_pdh_break", dict(), tfs=("H1",))
    j += J("b3", "pdh_break_tp1.5", "build_pdh_break", dict(tp_atr=1.5, sl_atr=0.5), tfs=("H1",))
    j += J("b3", "nr7_break", "build_nr_break", dict(), tfs=("H1",))
    j += J("b3", "nr4_break", "build_nr_break", dict(n=4), tfs=("H1",))
    j += J("b3", "inside_break", "build_nr_break", dict(inside=True), tfs=("H1",))
    j += J("b3", "nr7_break_mid", "build_nr_break", dict(sl="mid", tp_mult=1.5), tfs=("H1",))
    j += J("b3", "donchian20_h4", "build_donchian", dict(), tfs=("H4",))
    j += J("b3", "donchian55_h4", "build_donchian", dict(n=55, trail=4.0), tfs=("H4",))
    j += J("b3", "donchian20_d1", "build_donchian", dict(n=20, trail=3.0), tfs=("D1",))
    j += J("b3", "donchian10_h4_long", "build_donchian", dict(n=10, trail=2.5, side="long"), tfs=("H4",))
    j += J("b3", "ema_pb_h4", "build_ema_pullback", dict(), tfs=("H4",))
    j += J("b3", "ema_pb_h1", "build_ema_pullback", dict(fast=20, slow=100, max_hold=48), tfs=("H1",))
    j += J("b3", "ema_pb_h4_r3", "build_ema_pullback", dict(tp_r=3.0), tfs=("H4",))
    j += J("b3", "carry_dip", "build_carry_dip", dict(), tfs=("D1",))
    j += J("b3", "carry_dip_trail", "build_carry_dip", dict(tp=None, trail=3.0, max_hold=20), tfs=("D1",))
    j += J("b3", "carry_dip_200", "build_carry_dip", dict(trend_n=200, dip_n=3), tfs=("D1",))
    return j


@batch("b4")   # session / hour structure
def _b4():
    j = []
    j += J("b4", "tokyo_fix_long", "build_tokyo_fix", dict(), tfs=("H1",))
    j += J("b4", "tokyo_fix_long_all", "build_tokyo_fix", dict(gotobi_only=False), tfs=("H1",))
    j += J("b4", "post_fix_short", "build_tokyo_fix", dict(entry_h=2.0, exit_h=5, side="short"), tfs=("H1",))
    j += J("b4", "post_fix_short_all", "build_tokyo_fix", dict(entry_h=2.0, exit_h=5, side="short", gotobi_only=False), tfs=("H1",))
    j += J("b4", "post_fix_short_m30", "build_tokyo_fix", dict(entry_h=2.5, exit_h=5, side="short"), tfs=("M30",))
    j += J("b4", "rollover_short", "build_rollover", dict(), tfs=("H1",))
    j += J("b4", "rollover_short_23", "build_rollover", dict(entry_h=23.0, exit_h=0), tfs=("H1",))
    j += J("b4", "rollover_short_m30", "build_rollover", dict(entry_h=23.0, exit_h=0), tfs=("M30",))
    j += J("b4", "preopen_long", "build_rollover", dict(entry_h=0.0, exit_h=1, side="long"), tfs=("H1",))
    j += J("b4", "preopen_long_m30", "build_rollover", dict(entry_h=0.5, exit_h=1, side="long"), tfs=("M30",))
    j += J("b4", "preopen_long_m30b", "build_rollover", dict(entry_h=1.0, exit_h=1, side="long"), tfs=("M30",))
    j += J("b4", "london_fade", "build_london_fade", dict(), tfs=("H1",))
    j += J("b4", "london_fade_k0.8", "build_london_fade", dict(k=0.8, sl_atr=0.4), tfs=("H1",))
    j += J("b4", "london_follow", "build_london_fade", dict(mode="follow"), tfs=("H1",))
    j += J("b4", "round_number_1", "build_round_number", dict(), tfs=("H1",))
    j += J("b4", "round_number_05", "build_round_number", dict(step=0.5), tfs=("H1",))
    j += J("b4", "round_number_m30", "build_round_number", dict(step=0.5, max_hold=16), tfs=("M30",))
    j += J("b4", "pwh_sweep_h4", "build_pwh_sweep", dict(), tfs=("H4",))
    j += J("b4", "pwh_sweep_h1", "build_pwh_sweep", dict(max_hold=48), tfs=("H1",))
    j += J("b4", "pwh_sweep_h4_wc", "build_pwh_sweep", dict(tp="wc"), tfs=("H4",))
    return j



@batch("b5")   # new ideas: streak fade, z-fade, London fakeout, trend-filtered Tokyo break, NY follow/fade
def _b5():
    j = []
    j += J("b5", "streak3_fade_d1", "build_streak_fade", dict(), tfs=("D1",))
    j += J("b5", "streak4_fade_d1", "build_streak_fade", dict(n=4, max_hold=4), tfs=("D1",))
    j += J("b5", "streak3_fade_d1_big", "build_streak_fade", dict(min_move=1.5, max_hold=3), tfs=("D1",))
    j += J("b5", "streak3_follow_d1", "build_streak_fade", dict(mode="follow"), tfs=("D1",))
    j += J("b5", "streak5_fade_h4", "build_streak_fade", dict(n=5, max_hold=8), tfs=("H4",))
    j += J("b5", "streak6_fade_h1", "build_streak_fade", dict(n=6, max_hold=12), tfs=("H1",))
    j += J("b5", "zfade_d1", "build_zfade", dict(), tfs=("D1",))
    j += J("b5", "zfade_d1_n20", "build_zfade", dict(n=20, z=2.0, max_hold=8), tfs=("D1",))
    j += J("b5", "zfade_h4", "build_zfade", dict(n=20, z=2.2, max_hold=18), tfs=("H4",))
    j += J("b5", "zfade_h1", "build_zfade", dict(n=48, z=2.5, max_hold=48), tfs=("H1",))
    j += J("b5", "london_fakeout", "build_london_fakeout", dict(), tfs=("H1",))
    j += J("b5", "london_fakeout_tokyo", "build_london_fakeout", dict(tp="tokyo", k=0.3), tfs=("H1",))
    j += J("b5", "london_fakeout_m30", "build_london_fakeout", dict(k=0.25, exit_h=14), tfs=("M30",))
    j += J("b5", "tokyo_break_trend", "build_tokyo_break_trend", dict(), tfs=("H1",))
    j += J("b5", "tokyo_break_trend50", "build_tokyo_break_trend", dict(trend_n=50, tp_mult=1.5), tfs=("H1",))
    j += J("b5", "tokyo_break_trail", "build_tokyo_break_trend", dict(trail=2.0, sl="mid"), tfs=("H1",))
    j += J("b5", "tokyo_break_m30", "build_tokyo_break_trend", dict(trend_n=20), tfs=("M30",))
    j += J("b5", "ny_follow", "build_ny_follow", dict(), tfs=("H1",))
    j += J("b5", "ny_fade", "build_ny_follow", dict(mode="fade"), tfs=("H1",))
    j += J("b5", "ny_follow_k0.8", "build_ny_follow", dict(k=0.8, tp_atr=0.4, sl_atr=0.4), tfs=("H1",))
    return j


@batch("b6")   # sweeps around the leaders: gap fade, RSI(2) counter D1, big-day fade at London
def _b6():
    j = []
    for mg in (0.1, 0.2, 0.3):
        for mh in (12, 24, 48):
            j += J("b6", f"gap_fade_g{mg}_h{mh}", "build_gap_fade", dict(min_gap=mg, max_hold=mh), tfs=("H1",))
    j += J("b6", "gap_fade_sl1.5", "build_gap_fade", dict(sl_mult=1.5), tfs=("H1",))
    j += J("b6", "gap_fade_sl0.7", "build_gap_fade", dict(sl_mult=0.7, min_sl=0.2), tfs=("H1",))
    j += J("b6", "gap_fade_m30", "build_gap_fade", dict(max_hold=48), tfs=("M30",))
    for lo, hi in ((5, 95), (15, 85), (20, 80)):
        j += J("b6", f"rsi2c_d1_{lo}_{hi}", "build_rsi2", dict(counter=True, lo=lo, hi=hi), tfs=("D1",))
    for sl in (1.0, 1.5, 3.0):
        j += J("b6", f"rsi2c_d1_sl{sl}", "build_rsi2", dict(counter=True, sl_atr=sl), tfs=("D1",))
    for ex in (3, 10):
        j += J("b6", f"rsi2c_d1_ex{ex}", "build_rsi2", dict(counter=True, exit_n=ex), tfs=("D1",))
    j += J("b6", "rsi2c_d1_hold5", "build_rsi2", dict(counter=True, max_hold=5), tfs=("D1",))
    j += J("b6", "rsi3c_d1", "build_rsi2", dict(counter=True, n=3, lo=15, hi=85), tfs=("D1",))
    j += J("b6", "rsi2c_d1_long", "build_rsi2", dict(counter=True, side="long"), tfs=("D1",))
    j += J("b6", "rsi2c_d1_short", "build_rsi2", dict(counter=True, side="short"), tfs=("D1",))
    j += J("b6", "rsi2t_d1_sma100", "build_rsi2", dict(trend_n=100), tfs=("D1",))
    j += J("b6", "rsi2t_d1_sma50", "build_rsi2", dict(trend_n=50), tfs=("D1",))
    j += J("b6", "bigday_ldn_k1.0", "build_bigday_fade", dict(k=1.0, entry_h=9.0, max_hold=14), tfs=("H1",))
    j += J("b6", "bigday_ldn_k1.5", "build_bigday_fade", dict(k=1.5, entry_h=9.0, max_hold=14), tfs=("H1",))
    j += J("b6", "bigday_ldn_tp0.3", "build_bigday_fade", dict(k=1.2, entry_h=9.0, max_hold=14, tp_frac=0.3, sl_atr=0.5), tfs=("H1",))
    j += J("b6", "bigday_ny_k1.2", "build_bigday_fade", dict(k=1.2, entry_h=16.0, max_hold=7), tfs=("H1",))
    return j


if __name__ == "__main__":
    names = sys.argv[1:] or ["smoke"]
    procs = 1 if names == ["smoke"] else int(os.environ.get("PROCS", "2"))
    for n in names:
        jobs = BATCHES[n]()
        print(f"== batch {n}: {len(jobs)} jobs", flush=True)
        run_jobs(jobs, procs)
