"""Market study + data-quality report for the JPY cross group (round 3).

    python -m research.search3.jpy_crosses.study > research/search3/jpy_crosses/study_out.txt

Everything here is descriptive, read on the scoring window (2024-10-20..now)
AND on the longer history so the two can be compared.
"""
from __future__ import annotations

import os
os.environ["PROP_OOS"] = "1"

import numpy as np
import pandas as pd

from research.prop import harness as H

SYMS = ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY"]


def quality(sym, tf):
    df = pd.read_csv(H.DATA / f"{sym.lower()}-{tf}.csv", parse_dates=["time"])
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    t = pd.DatetimeIndex(df.time)
    day = t.normalize()
    rng = (df.high - df.low).groupby(day).sum() if tf == "d1" else (df.high.groupby(day).max() - df.low.groupby(day).min())
    med = rng.rolling(60, min_periods=20).median()
    flat = rng[(rng < 0.05 * med)]
    zero_vol = int((df.tick_volume == 0).sum())
    gaps = t.to_series().diff()
    step = {"m30": 0.5, "h1": 1, "h4": 4, "d1": 24}[tf]
    big = gaps[gaps > pd.Timedelta(hours=step * 2 + 48)]  # longer than a weekend
    return dict(sym=sym, tf=tf, bars=len(df), first=str(t[0]), last=str(t[-1]),
                flat_days=len(flat), flat_list=[str(x.date()) for x in flat.index[:10]],
                zero_vol_bars=zero_vol, long_gaps=len(big),
                gap_list=[f"{str(k.date())}:{v}" for k, v in big.items()][:8])


def study(sym):
    df = H.load(sym, "H1", split="oos")
    t = pd.DatetimeIndex(df.time)
    r = np.log(df.close).diff() * 1e4  # bp
    oos = df.time >= H.OOS_START
    d = pd.DataFrame({"r": r, "hr": t.hour, "wd": t.dayofweek, "oos": oos,
                      "rng": (df.high - df.low) / df.close * 1e4})
    o = d[d.oos]
    out = [f"\n=== {sym} (scoring window, H1) ==="]
    by_h = o.groupby("hr").agg(mean=("r", "mean"), sd=("r", "std"), rng=("rng", "mean"))
    out.append("hour: mean bp / sd bp / avg range bp")
    out.append(" ".join(f"{h:02d}:{m["mean"]:+.1f}/{m["sd"]:.0f}/{m["rng"]:.0f}" for h, m in by_h.iterrows()))
    by_w = o.groupby("wd").agg(mean=("r", "sum"), sd=("r", "std"))
    out.append("weekday total drift bp (Mon..Fri): " + " ".join(f"{m['mean']:+.0f}" for _, m in by_w.iterrows()))
    # sessions
    ses = {"tokyo 00-09": (0, 9), "london 09-16": (9, 16), "ny 16-23": (16, 23)}
    for k, (a, b) in ses.items():
        s = o[(o.hr >= a) & (o.hr < b)]
        out.append(f"{k}: mean {s.r.mean():+.2f} bp/bar, sd {s.r.std():.0f}, total drift {s.r.sum():+.0f} bp")
    # autocorrelation at several horizons: sign of persistence
    for tf, nm in (("H1", "H1"), ("H4", "H4"), ("D1", "D1")):
        x = H.load(sym, tf, split="oos")
        x = x[x.time >= H.OOS_START]
        rr = np.log(x.close).diff().dropna()
        ac1 = rr.autocorr(1)
        ac5 = rr.autocorr(5)
        # variance ratio 5 bars
        vr = rr.rolling(5).sum().dropna().var() / (5 * rr.var())
        out.append(f"{nm}: ac1 {ac1:+.3f} ac5 {ac5:+.3f} VR(5) {vr:.2f}  ({'trend' if vr > 1.05 else 'meanrev' if vr < 0.95 else 'random'})")
    # gap behaviour: Monday open vs Friday close (D1)
    dd = H.load(sym, "D1", split="oos")
    dd = dd[dd.time >= H.OOS_START].reset_index(drop=True)
    gap = (dd.open - dd.close.shift()) / dd.close.shift() * 1e4
    mon = pd.DatetimeIndex(dd.time).dayofweek == 0
    g = gap[mon]
    fill = ((dd.close - dd.open) * np.sign(-gap))[mon] / dd.close.shift()[mon] * 1e4
    out.append(f"Monday gap: mean abs {g.abs().mean():.1f} bp, same-day move against gap {fill.mean():+.1f} bp (n={mon.sum()})")
    # Tokyo fix 02:55 effect: 00:00-03:00 drift vs 03:00-09:00 (gotobi days)
    dayn = t.day
    goto = np.isin(dayn, [5, 10, 15, 20, 25, 30]) & (t.dayofweek < 5)
    pre = o[(o.hr >= 0) & (o.hr < 3)]
    pre_g = pre[goto[o.index[(o.hr >= 0) & (o.hr < 3)]]]
    post = o[(o.hr >= 3) & (o.hr < 6)]
    post_g = post[goto[o.index[(o.hr >= 3) & (o.hr < 6)]]]
    out.append(f"pre-fix 00-03 drift: all {pre.r.mean():+.2f} bp/bar, gotobi {pre_g.r.mean():+.2f}; post-fix 03-06: all {post.r.mean():+.2f}, gotobi {post_g.r.mean():+.2f}")
    # day-type: how often does the London/NY session continue the Tokyo direction
    o = o.assign(day=t[o.index].normalize())
    tok = o[(o.hr >= 0) & (o.hr < 9)].groupby("day").r.sum()
    rest = o[(o.hr >= 9) & (o.hr < 23)].groupby("day").r.sum()
    j = pd.concat([tok, rest], axis=1, keys=["tok", "rest"]).dropna()
    out.append(f"Tokyo->rest-of-day sign agreement {np.mean(np.sign(j.tok) == np.sign(j.rest)):.2f}, corr {j.tok.corr(j.rest):+.2f}")
    ldn = o[(o.hr >= 9) & (o.hr < 16)].groupby("day").r.sum()
    ny = o[(o.hr >= 16) & (o.hr < 23)].groupby("day").r.sum()
    j = pd.concat([ldn, ny], axis=1, keys=["l", "n"]).dropna()
    out.append(f"London->NY sign agreement {np.mean(np.sign(j.l) == np.sign(j.n)):.2f}, corr {j.l.corr(j.n):+.2f}")
    # prior-day high/low: how often touched, how often closes beyond
    hi = dd.high.shift(); lo = dd.low.shift()
    touch_h = (dd.high >= hi).mean(); touch_l = (dd.low <= lo).mean()
    close_above = (dd.close > hi).mean(); close_below = (dd.close < lo).mean()
    out.append(f"prior-day high touched {touch_h:.2f}, closed above {close_above:.2f} | low touched {touch_l:.2f}, closed below {close_below:.2f}")
    both = ((dd.high >= hi) & (dd.low <= lo)).mean()
    out.append(f"both prior extremes taken same day {both:.2f}; inside days {((dd.high < hi) & (dd.low > lo)).mean():.2f}")
    # vol regime
    atr = (dd.high - dd.low).rolling(14).mean() / dd.close * 1e4
    out.append(f"D1 ATR14 bp: median {atr.median():.0f}, p10 {atr.quantile(.1):.0f}, p90 {atr.quantile(.9):.0f}")
    # co-movement with US500 (risk on/off)
    try:
        us = pd.read_csv(H.DATA / "us500-d1.csv", parse_dates=["time"]).drop_duplicates("time")
        us = us[us.time >= H.OOS_START]
        a = pd.Series(np.log(dd.close.values), index=pd.DatetimeIndex(dd.time).normalize()).diff()
        b = pd.Series(np.log(us.close.values), index=pd.DatetimeIndex(us.time).normalize()).diff()
        jj = pd.concat([a, b], axis=1).dropna()
        out.append(f"corr with US500 daily: same-day {jj.iloc[:, 0].corr(jj.iloc[:, 1]):+.2f}, lag1 (US500 t-1 -> pair t) {jj.iloc[:, 0].corr(jj.iloc[:, 1].shift()):+.2f}")
    except Exception as e:  # noqa
        out.append(f"US500 corr failed: {e}")
    return "\n".join(out)


if __name__ == "__main__":
    print("# DATA QUALITY")
    for s in SYMS:
        for tf in ("m30", "h1", "h4", "d1"):
            q = quality(s, tf)
            print(q)
    for s in SYMS:
        print(study(s))
