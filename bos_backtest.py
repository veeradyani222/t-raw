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

import pandas as pd

import wf_search as wf
from trader.config import Config

PIP, PIP_VALUE, SPREAD = wf.PIP, wf.PIP_VALUE, wf.SPREAD


# --------------------------------------------------------------------------- #
# Data (WITH volume — CMF needs tick_volume)                                  #
# --------------------------------------------------------------------------- #
def load_vol(tf, start="2017-01-01", end="2026-08-22") -> pd.DataFrame:
    cfg = Config(symbol=wf.SYM, timeframe=tf, strategy="orb",
                 pip_size=PIP, pip_value_per_lot=PIP_VALUE, spread_pips=SPREAD)
    df = wf.bt.load_history(cfg, pd.Timestamp(start), pd.Timestamp(end), None,
                            need_volume=True)
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Break-of-structure signal — FAST research path.                              #
# Precomputes swings + CMF once (heavy work) and, on each bar, applies the      #
# SAME rules as the live trader.strategies.bos.compute_signal on a rolling      #
# `lookback` window: the TP-target search is bounded to that window exactly as  #
# the live module (which only sees `lookback` bars) does. test_bos.py asserts   #
# this reproduces bos.compute_signal decision-for-decision on real data, so the #
# walk-forward / prop numbers here and the live signals are the same strategy.  #
# --------------------------------------------------------------------------- #
import numpy as np  # noqa: E402
from trader.strategies.orb import swing_points  # noqa: E402


def _confirmed_last(swings, window, n):
    """last[i] = most recent swing index j with j+window <= i (confirmed by bar
    i); -1 where none. This is what prevents lookahead."""
    last = np.full(n, -1, dtype=int)
    p, cur = 0, -1
    for i in range(n):
        while p < len(swings) and swings[p] + window <= i:
            cur = swings[p]
            p += 1
        last[i] = cur
    return last


def make_bos_signal(df, *, swing_window=2, cmf_n=20, tp_mode="structure", tp_r=3.0,
                    tp_min_r=1.0, use_cmf=True, cmf_min=0.0, trend_ma=0, lookback=2000):
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)
    openp = df["open"].values.astype(float)
    vol = df["tick_volume"].values.astype(float)
    n = len(df)
    L = lookback

    sh_idx, sl_idx = swing_points(high, low, swing_window)
    last_high = _confirmed_last(sh_idx, swing_window, n)
    last_low = _confirmed_last(sl_idx, swing_window, n)
    # The live module only sees `lookback` bars, so a swing is usable at bar i
    # only if its whole fractal (index +/- swing_window) fits in that window:
    # j >= i - L + 1 + swing_window. Drop older ones so this matches exactly.
    idx = np.arange(n)
    floor = idx - L + 1 + swing_window
    last_high = np.where(last_high >= floor, last_high, -1)
    last_low = np.where(last_low >= floor, last_low, -1)
    rng = high - low
    mfm = np.where(rng > 0, ((close - low) - (high - close)) / np.where(rng > 0, rng, 1.0), 0.0)
    smfv = pd.Series(mfm * vol).rolling(cmf_n).sum().values
    svol = pd.Series(vol).rolling(cmf_n).sum().values
    c = np.where(svol > 0, smfv / np.where(svol > 0, svol, 1.0), np.nan)
    ma = pd.Series(close).rolling(trend_ma).mean().values if trend_ma > 0 else None
    cmin = -1.0 if not use_cmf else cmf_min
    sh_arr = np.array(sh_idx, dtype=int)
    sl_arr = np.array(sl_idx, dtype=int)

    min_bars = max(cmf_n, swing_window * 2) + 2   # matches bos.compute_signal's guard

    def sig(_df, i):
        # The live module only has min(L, i+1) bars at bar i; honour its guard.
        if i < 1 or min(L, i + 1) < min_bars:
            return None
        hi = last_high[i]
        if hi >= 0:
            lvl = high[hi]
            if close[i] > lvl and close[i - 1] <= lvl and close[i] > openp[i] \
                    and not np.isnan(c[i]) and c[i] > cmin \
                    and (ma is None or (not np.isnan(ma[i]) and close[i] > ma[i])):
                lo = last_low[i]
                if lo >= 0 and low[lo] < close[i]:
                    sl = low[lo]; risk = close[i] - sl
                    if risk > 0:
                        tp = close[i] + tp_r * risk
                        if tp_mode == "structure":
                            cand = sh_arr[(sh_arr + swing_window <= i)
                                          & (sh_arr - swing_window >= i - L + 1)
                                          & (high[sh_arr] >= close[i] + tp_min_r * risk)]
                            if cand.size:
                                tp = float(high[cand].min())
                        return wf.Entry("long", sl=float(sl), tp=float(tp), meta={})
        lo = last_low[i]
        if lo >= 0:
            lvl = low[lo]
            if close[i] < lvl and close[i - 1] >= lvl and close[i] < openp[i] \
                    and not np.isnan(c[i]) and c[i] < -cmin \
                    and (ma is None or (not np.isnan(ma[i]) and close[i] < ma[i])):
                hi = last_high[i]
                if hi >= 0 and high[hi] > close[i]:
                    sl = high[hi]; risk = sl - close[i]
                    if risk > 0:
                        tp = close[i] - tp_r * risk
                        if tp_mode == "structure":
                            cand = sl_arr[(sl_arr + swing_window <= i)
                                          & (sl_arr - swing_window >= i - L + 1)
                                          & (low[sl_arr] <= close[i] - tp_min_r * risk)]
                            if cand.size:
                                tp = float(low[cand].max())
                        return wf.Entry("short", sl=float(sl), tp=float(tp), meta={})
        return None

    return sig


# --------------------------------------------------------------------------- #
# A-priori config (chosen from theory, NOT tuned per fold)                     #
# --------------------------------------------------------------------------- #
APRIORI = dict(swing_window=2, cmf_n=20, tp_mode="structure", tp_r=3.0, tp_min_r=1.0,
               lookback=2000)
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


# --------------------------------------------------------------------------- #
# C: STRENGTHEN — compare a-priori levers, judged full-history AND fixed-config #
#    out-of-sample (NOTHING tuned per fold, so the OOS number can't overfit).   #
# --------------------------------------------------------------------------- #
def fixed_oos(df, cfg, **fold_kw):
    """Run ONE fixed config on each walk-forward TEST fold; aggregate. No
    training => no optimizer overfit. The honest OOS score of an a-priori rule."""
    fs = wf.folds(df, **fold_kw)
    rows = [wf.simulate(test, make_bos_signal(test, **cfg)) for _, test, _ in fs]
    net = sum(r["net"] for r in rows)
    tot = sum(r["trades"] for r in rows)
    pos = sum(1 for r in rows if r["net"] > 0)
    return net, tot, pos, len(rows)


STRENGTHEN_VARIANTS = {
    "baseline (cmf>0)":        dict(APRIORI),
    "cmf_min 0.05":           {**APRIORI, "cmf_min": 0.05},
    "cmf_min 0.10":           {**APRIORI, "cmf_min": 0.10},
    "trend MA50":             {**APRIORI, "trend_ma": 50},
    "trend MA100":            {**APRIORI, "trend_ma": 100},
    "trend MA200":            {**APRIORI, "trend_ma": 200},
    "MA100 + cmf_min 0.05":   {**APRIORI, "trend_ma": 100, "cmf_min": 0.05},
    "MA200 + cmf_min 0.05":   {**APRIORI, "trend_ma": 200, "cmf_min": 0.05},
}


def run_strengthen():
    df = load_vol("H1")
    print("#" * 78)
    print("# C: STRENGTHEN the H1 edge — a-priori levers (no per-fold tuning)")
    print("#   full = whole 9.5yr | OOS = same config on 15 test folds only (honest)")
    print("#" * 78)
    print(f"{'variant':<24}{'trades':>7}{'win%':>7}{'fullNet$':>10}{'maxDD$':>9}"
          f"{'posYr':>7}{'  | OOS net$':>12}{'OOSpos':>8}")
    for name, cfg in STRENGTHEN_VARIANTS.items():
        r = wf.simulate(df, make_bos_signal(df, **cfg))
        t = r["trade_log"]
        py = ny = 0
        if not t.empty:
            by = t.groupby(pd.DatetimeIndex(t["entry_time"]).year)["profit"].sum()
            py, ny = int((by > 0).sum()), len(by)
        onet, otot, opos, ofolds = fixed_oos(df, cfg, train_years=2,
                                              test_months=6, step_months=6)
        print(f"{name:<24}{r['trades']:>7}{r['win_rate']*100:>6.1f}%{r['net']:>+10.0f}"
              f"{r['max_dd']:>+9.0f}{py:>5}/{ny}{onet:>+12.0f}{opos:>5}/{ofolds}")


# --------------------------------------------------------------------------- #
# A: SPREAD STRESS — does the edge survive 2x-3x the assumed gold spread?      #
# B: PROP RAILS   — real drawdown vs the firm's 4% daily / 8% total limits.    #
# BEST is set from the strengthen run below.                                   #
# --------------------------------------------------------------------------- #
BEST = dict(APRIORI)  # overwritten via `set_best` after we see C's winner


def run_spread(cfg=None):
    cfg = cfg or BEST
    df = load_vol("H1")
    yr = df[df["time"] >= df["time"].max() - pd.DateOffset(months=12)].reset_index(drop=True)
    print("#" * 70)
    print(f"# A: SPREAD STRESS on H1  config={cfg}")
    print(f"# base gold spread = {SPREAD} pips ($0.30/oz). Round-trip cost scales with it.")
    print("#" * 70)
    print(f"{'spread(pips)':>13}{'12mo net$':>12}{'full net$':>12}{'full win%':>11}{'fullDD$':>10}")
    for sp in [SPREAD, 4.5, 6.0, 9.0, 12.0]:
        r12 = wf.simulate(yr, make_bos_signal(yr, **cfg), spread=sp)
        rall = wf.simulate(df, make_bos_signal(df, **cfg), spread=sp)
        mark = "  <- base" if sp == SPREAD else ("  (2x)" if sp == 6.0 else ("  (3x)" if sp == 9.0 else ""))
        print(f"{sp:>13.1f}{r12['net']:>+12.0f}{rall['net']:>+12.0f}"
              f"{rall['win_rate']*100:>10.1f}%{rall['max_dd']:>+10.0f}{mark}")


def run_prop(cfg=None):
    cfg = cfg or BEST
    df = load_vol("H1")
    print("#" * 70)
    print(f"# B: PROP RAILS on H1  config={cfg}")
    print("#   live-bot buffered rails: 1% risk, daily halt -3%, total halt -6% ($10k)")
    print("#" * 70)
    RAILS = dict(risk=0.01, daily_halt=0.03, loss_baseline=10_000.0, total_halt=0.06)
    for label, sub in [("LAST 12 MONTHS", df[df["time"] >= df["time"].max() - pd.DateOffset(months=12)].reset_index(drop=True)),
                       ("LAST 3 YEARS", df[df["time"] >= df["time"].max() - pd.DateOffset(years=3)].reset_index(drop=True)),
                       ("FULL HISTORY (all regimes)", df)]:
        r = wf.simulate(sub, make_bos_signal(sub, **cfg), start_equity=10_000.0, **RAILS)
        t = r["trade_log"].copy()
        worst_day = dd_base = 0.0
        if not t.empty:
            t["day"] = pd.DatetimeIndex(t["entry_time"]).date
            daily = t.groupby("day").agg(pnl=("profit", "sum"), eq_end=("equity_after", "last"))
            daily["eq_start"] = daily["eq_end"] - daily["pnl"]
            worst_day = float((daily["pnl"] / daily["eq_start"] * 100).min())
            eq = 10_000 + t["profit"].cumsum()
            dd_base = float(((eq - 10_000) / 10_000 * 100).min())
        ret = r["net"] / 10_000 * 100
        print(f"\n=== {label} ===  ({len(sub)} bars)")
        print(f"  trades {r['trades']}  win {r['win_rate']*100:.1f}%  net {r['net']:+.0f} ({ret:+.1f}%)")
        print(f"  worst single day: {worst_day:+.2f}% (limit -3% buffered)  "
              f"max DD from start: {dd_base:+.2f}% (limit -6%)")
        print(f"  prop breach: {'YES @ '+str(r['blown_at']) if r['blown_at'] else 'no (survived)'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "strengthen":
        run_strengthen(); sys.exit()
    if cmd == "spread":
        run_spread(); sys.exit()
    if cmd == "prop":
        run_prop(); sys.exit()
    if cmd in ("fixed", "all"):
        run_fixed()
    if cmd in ("cmf_ab", "all"):
        run_cmf_ab()
    if cmd in ("wf", "all"):
        run_wf()
    if cmd not in ("fixed", "cmf_ab", "wf", "all"):
        print(f"unknown command {cmd!r}; try: fixed | cmf_ab | wf | all")
