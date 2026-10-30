"""Market study + data quality for the asia_indices group (JPN225 HK50 CHINA50 AUS200).
Run: python research/search3/asia_indices/study.py  -> prints a report (pasted into NOTES.md)."""
from __future__ import annotations
import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import numpy as np, pandas as pd
from research.search3.asia_indices import strategies as S  # applies harness patches
from research.prop import harness as H

SYMS = ["JPN225", "HK50", "CHINA50", "AUS200"]


def quality(sym):
    out = {}
    for tf in ("M30", "H1", "H4", "D1"):
        df = H.load(sym, tf, split="all")
        d = df[df.time >= "2024-10-20"]
        rng = (d.high - d.low)
        if tf == "D1":
            med = rng.median()
            flat = int((rng < 0.05 * med).sum())
        else:
            dd = d.groupby(d.time.dt.normalize()).agg(h=("high", "max"), l=("low", "min"))
            r = dd.h - dd.l
            flat = int((r < 0.05 * r.median()).sum())
        gaps = d.time.diff().dt.total_seconds() / 3600
        step = {"M30": 0.5, "H1": 1, "H4": 4, "D1": 24}[tf]
        long_gaps = int((gaps > max(72, step * 3)).sum())   # > weekend
        zero_vol = int((d.tick_volume == 0).sum())
        out[tf] = dict(bars=len(d), flat_days=flat, long_gaps=long_gaps, zero_vol=zero_vol,
                       first=str(df.time.iloc[0])[:10], last=str(df.time.iloc[-1])[:16])
    return out


def hour_study(sym):
    df = H.load(sym, "H1", split="all")
    df = df[df.time >= "2022-01-01"].copy()
    r = np.log(df.close / df.open) * 1e4
    df["r"] = r; df["rng"] = (df.high - df.low) / df.close * 1e4
    df["hour"] = df.time.dt.hour
    g = df.groupby("hour").agg(mean_bp=("r", "mean"), sd_bp=("r", "std"), rng_bp=("rng", "mean"), n=("r", "size"),
                               vol=("tick_volume", "mean"))
    g["t"] = g.mean_bp / g.sd_bp * np.sqrt(g.n)
    # persistence: corr of this hour's return with next hour's return
    df["r_next"] = df.r.shift(-1)
    ac = df.groupby("hour").apply(lambda x: x.r.corr(x.r_next))
    g["ac_next"] = ac
    return g.round(2)


def weekday_study(sym):
    df = H.load(sym, "D1", split="all")
    df = df[df.time >= "2022-01-01"].copy()
    df["r"] = np.log(df.close / df.open) * 1e4
    df["wd"] = df.time.dt.dayofweek
    g = df.groupby("wd").agg(mean_bp=("r", "mean"), sd=("r", "std"), n=("r", "size"))
    g["t"] = g.mean_bp / g.sd * np.sqrt(g.n)
    return g.round(2)


def persistence(sym):
    rows = {}
    for tf in ("M30", "H1", "H4", "D1"):
        df = H.load(sym, tf, split="all")
        df = df[df.time >= "2022-01-01"]
        r = np.log(df.close).diff().dropna()
        rows[tf] = dict(ac1=round(r.autocorr(1), 3), ac2=round(r.autocorr(2), 3),
                        var_ratio_5=round(float(r.rolling(5).sum().dropna().var() / (5 * r.var())), 3))
    return rows


def session_study(sym, open_h, close_h):
    """Cash-session stats on H1: overnight gap (prev cash close -> cash open bar open),
    gap fill rate same session, open-drive (first hour direction continues to close?)."""
    df = H.load(sym, "H1", split="all")
    df = df[df.time >= "2022-01-01"].copy()
    df["day"] = df.time.dt.normalize(); df["hour"] = df.time.dt.hour
    res = []
    prev_close = None
    for day, d in df.groupby("day"):
        d = d.set_index("hour")
        if open_h not in d.index or close_h not in d.index:
            continue
        o = d.loc[open_h, "open"]; c = d.loc[close_h, "close"]
        first_h = d.loc[open_h]
        sess = d.loc[open_h:close_h]
        if prev_close is not None:
            gap = o - prev_close
            filled = (sess.low.min() <= prev_close) if gap > 0 else (sess.high.max() >= prev_close)
            fh = first_h.close - first_h.open
            res.append(dict(gap=gap / o * 1e4, filled=bool(filled), fh=fh / o * 1e4,
                            rest=(c - first_h.close) / o * 1e4, sess=(c - o) / o * 1e4))
        prev_close = c
    r = pd.DataFrame(res)
    big = r[r.gap.abs() > r.gap.abs().median()]
    return dict(n=len(r), gap_abs_med_bp=round(r.gap.abs().median(), 1),
                fill_rate_all=round(r.filled.mean(), 3), fill_rate_big=round(big.filled.mean(), 3),
                gap_vs_session_corr=round(r.gap.corr(r.sess), 3),
                first_hour_vs_rest_corr=round(r.fh.corr(r.rest), 3),
                session_mean_bp=round(r.sess.mean(), 2), session_t=round(r.sess.mean() / r.sess.std() * np.sqrt(len(r)), 2))


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    for sym in SYMS:
        print("=" * 80, "\n", sym)
        print("QUALITY (scored window 2024-10-20..):")
        for tf, q in quality(sym).items():
            print("  ", tf, q)
        print("PERSISTENCE (2022+):", persistence(sym))
        print("WEEKDAY D1 (bp, 2022+):\n", weekday_study(sym))
        print("HOUR H1 (bp, 2022+):\n", hour_study(sym))
        for name, (oh, ch) in {"JPN225": [(3, 8), (2, 7)], "HK50": [(4, 10), (3, 9)],
                               "CHINA50": [(4, 10), (3, 9)], "AUS200": [(3, 8), (2, 7)]}[sym] and \
                {"A": {"JPN225": (3, 8), "HK50": (4, 10), "CHINA50": (4, 10), "AUS200": (3, 8)}[sym],
                 "B": {"JPN225": (2, 7), "HK50": (3, 9), "CHINA50": (3, 9), "AUS200": (2, 7)}[sym]}.items():
            print(f"SESSION {name} open={oh} close={ch}:", session_study(sym, oh, ch))
