"""Break-of-Structure + Chaikin Money Flow on gold — ISOLATED research harness.

Does NOT touch engine.py / sim.py / live. Reuses the VALIDATED cost/risk model
(`wf_search.simulate`: entry at close +- spread, SL/TP filled against later bars
with SL winning ties, 1% sizing via trader.risk.position_size_lots) plus the
fractal `swing_points`, `folds`, `walk_forward`, and `per_year` helpers — the same
building blocks that reproduce trader.sim on ORB with 0 differing decisions.

Strategy (see docs/2026-08-23-gold-bos-cmf-design.md):
  - mark the most recent CONFIRMED fractal swing high / swing low
  - LONG when a candle CLOSES above the swing high (fresh cross, bullish bar);
    SHORT when it closes below the swing low (fresh cross, bearish bar)
  - CMF must agree: CMF>0 for longs, CMF<0 for shorts (opt-out with use_cmf=False)
  - stop = far side of broken structure (opposing confirmed swing); TP = next
    confirmed swing beyond entry (>= tp_min_r x risk), else tp_r x risk fallback

    python bos_backtest.py fixed     # a-priori config, per-year, every timeframe
    python bos_backtest.py cmf_ab    # same BOS with CMF ON vs OFF (isolate CMF)
    python bos_backtest.py wf        # walk-forward on H1 (the only real test)
    python bos_backtest.py all       # all of the above
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("WF_SYM", "XAUUSD")  # must precede wf_search import

import numpy as np
import pandas as pd

import wf_search as wf
from trader.config import Config
from trader.strategies.orb import swing_points

PIP, PIP_VALUE, SPREAD = wf.PIP, wf.PIP_VALUE, wf.SPREAD


# --------------------------------------------------------------------------- #
# Data (WITH volume — CMF needs tick_volume)                                  #
# --------------------------------------------------------------------------- #
def load_vol(tf, start="2017-01-01", end="2026-08-22") -> pd.DataFrame:
    cfg = Config(symbol="XAUUSD", timeframe=tf, strategy="orb",
                 pip_size=PIP, pip_value_per_lot=PIP_VALUE, spread_pips=SPREAD)
    df = wf.bt.load_history(cfg, pd.Timestamp(start), pd.Timestamp(end), None,
                            need_volume=True)
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Chaikin Money Flow (no lookahead: value at i uses only bars i-n+1..i)        #
# --------------------------------------------------------------------------- #
def cmf(df: pd.DataFrame, n: int = 20) -> np.ndarray:
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)
    vol = df["tick_volume"].values.astype(float)
    rng = high - low
    # money-flow multiplier: +1 close at high, -1 close at low, 0 if flat bar
    safe = np.where(rng > 0, rng, 1.0)
    mfm = np.where(rng > 0, ((close - low) - (high - close)) / safe, 0.0)
    mfv = mfm * vol
    s_mfv = pd.Series(mfv).rolling(n).sum().values
    s_vol = pd.Series(vol).rolling(n).sum().values
    return np.where(s_vol > 0, s_mfv / np.where(s_vol > 0, s_vol, 1.0), np.nan)


# --------------------------------------------------------------------------- #
# Break-of-structure signal                                                   #
# --------------------------------------------------------------------------- #
def _confirmed_last(swings: list[int], window: int, n: int) -> np.ndarray:
    """last_idx[i] = the most recent swing index j (from `swings`) that is
    CONFIRMED by bar i, i.e. j + window <= i (needs `window` bars to its right).
    -1 where none yet. This is what prevents lookahead."""
    last = np.full(n, -1, dtype=int)
    p, cur = 0, -1
    for i in range(n):
        while p < len(swings) and swings[p] + window <= i:
            cur = swings[p]
            p += 1
        last[i] = cur
    return last


def make_bos_signal(df, *, swing_window=2, cmf_n=20, tp_mode="structure",
                    tp_r=3.0, tp_min_r=1.0, use_cmf=True):
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)
    openp = df["open"].values.astype(float)
    n = len(df)

    sh_idx, sl_idx = swing_points(high, low, swing_window)   # confirmed fractals
    last_high = _confirmed_last(sh_idx, swing_window, n)        # resistance to break
    last_low = _confirmed_last(sl_idx, swing_window, n)         # support to break
    c = cmf(df, cmf_n)
    sh_arr = np.array(sh_idx, dtype=int)
    sl_arr = np.array(sl_idx, dtype=int)

    def sig(_df, i):
        if i < 1:
            return None

        # ---- LONG: fresh close above the last confirmed swing high ----------
        hi = last_high[i]
        if hi >= 0:
            level = high[hi]
            crossed = close[i] > level and close[i - 1] <= level
            bullish = close[i] > openp[i]
            cmf_ok = (not use_cmf) or (not np.isnan(c[i]) and c[i] > 0)
            if crossed and bullish and cmf_ok:
                lo = last_low[i]
                if lo >= 0 and low[lo] < close[i]:
                    sl = low[lo]
                    risk = close[i] - sl
                    if risk > 0:
                        # TP: nearest CONFIRMED swing high above entry+min_r*risk
                        tp = close[i] + tp_r * risk
                        src = "r_mult"
                        cand = sh_arr[(sh_arr + swing_window <= i) &
                                      (high[sh_arr] >= close[i] + tp_min_r * risk)]
                        if tp_mode == "structure" and cand.size:
                            tp = float(high[cand].min())  # nearest resistance up
                            src = "structure"
                        return wf.Entry("long", sl=float(sl), tp=float(tp),
                                        meta={"cmf": round(float(c[i]), 3) if not np.isnan(c[i]) else None,
                                              "tp_src": src})

        # ---- SHORT: fresh close below the last confirmed swing low -----------
        lo = last_low[i]
        if lo >= 0:
            level = low[lo]
            crossed = close[i] < level and close[i - 1] >= level
            bearish = close[i] < openp[i]
            cmf_ok = (not use_cmf) or (not np.isnan(c[i]) and c[i] < 0)
            if crossed and bearish and cmf_ok:
                hi = last_high[i]
                if hi >= 0 and high[hi] > close[i]:
                    sl = high[hi]
                    risk = sl - close[i]
                    if risk > 0:
                        tp = close[i] - tp_r * risk
                        src = "r_mult"
                        cand = sl_arr[(sl_arr + swing_window <= i) &
                                      (low[sl_arr] <= close[i] - tp_min_r * risk)]
                        if tp_mode == "structure" and cand.size:
                            tp = float(low[cand].max())  # nearest support down
                            src = "structure"
                        return wf.Entry("short", sl=float(sl), tp=float(tp),
                                        meta={"cmf": round(float(c[i]), 3) if not np.isnan(c[i]) else None,
                                              "tp_src": src})
        return None

    return sig


# --------------------------------------------------------------------------- #
# A-priori config (chosen from theory, NOT tuned per fold)                     #
# --------------------------------------------------------------------------- #
APRIORI = dict(swing_window=2, cmf_n=20, tp_mode="structure", tp_r=3.0, tp_min_r=1.0)
TIMEFRAMES = ["H1", "M30", "M15", "M5"]


def run_fixed():
    print("#" * 70)
    print("# A-PRIORI BOS+CMF (structure exit), per-year, every timeframe")
    print(f"# fixed params: {APRIORI}")
    print("#" * 70)
    for tf in TIMEFRAMES:
        try:
            df = load_vol(tf)
        except Exception as e:
            print(f"\n#### {tf}: SKIP (no data — {type(e).__name__}: {e})")
            continue
        yrs = df["time"].dt.year.nunique()
        note = "" if tf == "H1" else "  <-- fixed-param only (no walk-forward on this TF)"
        print(f"\n#### TIMEFRAME {tf}  ({len(df)} bars, {yrs} yr){note}")
        wf.per_year(f"BOS+CMF {tf}", df,
                    lambda d: make_bos_signal(d, **APRIORI))


def run_cmf_ab():
    print("#" * 70)
    print("# CMF A/B — same BOS, CMF ON vs OFF (does the volume filter help?)")
    print("#" * 70)
    for tf in TIMEFRAMES:
        try:
            df = load_vol(tf)
        except Exception as e:
            print(f"\n#### {tf}: SKIP ({type(e).__name__})")
            continue
        print(f"\n#### TIMEFRAME {tf}  ({len(df)} bars)")
        for use in (True, False):
            r = wf.simulate(df, make_bos_signal(df, **{**APRIORI, "use_cmf": use}))
            tag = "CMF ON " if use else "CMF OFF"
            print(f"  {tag}: trades={r['trades']:<5} win={r['win_rate']*100:>5.1f}%  "
                  f"net={r['net']:>+9.0f}  maxDD={r['max_dd']:>+8.0f}")


# --------------------------------------------------------------------------- #
# Walk-forward (H1 only — the sole timeframe with enough history)              #
# --------------------------------------------------------------------------- #
BOS_GRID = [dict(swing_window=sw, cmf_n=cn, tp_mode="structure", tp_r=3.0, tp_min_r=1.0)
            for sw in (2, 3) for cn in (14, 20)]


def bos_search(train_df, min_trades=15):
    best, best_net = None, -1e18
    for p in BOS_GRID:
        r = wf.simulate(train_df, make_bos_signal(train_df, **p))
        if r["trades"] >= min_trades and r["net"] > best_net:
            best, best_net = p, r["net"]
    return best


def run_wf():
    df = load_vol("H1")
    wf.walk_forward("BOS+CMF H1", df, bos_search,
                    lambda te, **p: make_bos_signal(te, **p),
                    train_years=2, test_months=6, step_months=6)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("fixed", "all"):
        run_fixed()
    if cmd in ("cmf_ab", "all"):
        run_cmf_ab()
    if cmd in ("wf", "all"):
        run_wf()
    if cmd not in ("fixed", "cmf_ab", "wf", "all"):
        print(f"unknown command {cmd!r}; try: fixed | cmf_ab | wf | all")
