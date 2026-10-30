"""Market study + data-quality report for the majors group (round 3).
Writes study_out.txt. Scoring window 2024-10-20..now (OOS)."""
import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, ".")
import numpy as np, pandas as pd
from research.prop import harness as H

SYMS = ["EURUSD", "GBPUSD", "USDCHF", "EURGBP", "EURCHF", "GBPCHF"]
out = []
P = lambda *a: (print(*a), out.append(" ".join(str(x) for x in a)))

for s in SYMS:
    for tf in ("M30", "H1", "H4", "D1"):
        df = H.load(s, tf, split="all")
        t = pd.DatetimeIndex(df.time)
        gaps = t.to_series().diff().dt.total_seconds().div(3600)
        bar_h = {"M30": .5, "H1": 1, "H4": 4, "D1": 24}[tf]
        # gaps longer than a weekend (>= 60h) for intraday, or >4 days for D1
        big = gaps[gaps > (72 if tf != "D1" else 24 * 4.5)]
        zero = int((df.tick_volume == 0).sum())
        d = df.assign(day=t.normalize()).groupby("day").agg(h=("high", "max"), l=("low", "min"), n=("close", "size"))
        rng = d.h - d.l
        med = rng.rolling(60, min_periods=20).median()
        flat = d[(rng < 0.05 * med)]
        P(f"DQ {s} {tf}: bars={len(df)} {t[0].date()}..{t[-1].date()} zero_vol={zero} "
          f"flat_days={len(flat)} {list(flat.index.date)[:5]} long_gaps={len(big)} "
          f"{[(str(k.date()), round(v,1)) for k,v in big.items()][:5]}")

P("\n=== HOURLY study (H1, OOS window 2024-10-20..) ===")
for s in SYMS:
    df = H.load(s, "H1", split="oos"); df = df[df.time >= H.OOS_START]
    t = pd.DatetimeIndex(df.time)
    r = np.log(df.close / df.open) * 1e4
    rng = (df.high - df.low) * 1e4
    g = pd.DataFrame({"h": t.hour, "r": r, "rng": rng, "wd": t.dayofweek})
    hh = g.groupby("h").agg(mean_r=("r", "mean"), rng=("rng", "mean"), n=("r", "size"))
    P(f"\n{s} H1 by hour (mean ret pips, mean range pips):")
    P("  " + " ".join(f"{h:02d}:{m:+.2f}/{rg:.1f}" for h, m, rg in zip(hh.index, hh.mean_r, hh.rng)))
    wd = g.groupby("wd").agg(mean_r=("r", "mean"), rng=("rng", "mean"))
    P("  weekday mean ret / range: " + " ".join(f"{d}:{m:+.2f}/{rg:.1f}" for d, m, rg in zip(wd.index, wd.mean_r, wd.rng)))
    # sessions (server EET): asia 00-09, london 10-15, overlap 16-19, ny late 20-23
    sess = pd.cut(t.hour, [-1, 9, 15, 19, 23], labels=["asia00-09", "ldn10-15", "ovl16-19", "late20-23"])
    sg = g.assign(sess=sess).groupby("sess", observed=True).agg(mean_r=("r", "mean"), rng=("rng", "mean"), absr=("r", lambda x: x.abs().mean()))
    P("  sessions: " + " ".join(f"{k}:{m:+.2f}/rng{rg:.1f}/|r|{a:.1f}" for k, m, rg, a in zip(sg.index, sg.mean_r, sg.rng, sg.absr)))
    # autocorrelation of returns per TF (trend persistence vs mean reversion)
    for tf in ("M30", "H1", "H4", "D1"):
        d2 = H.load(s, tf, split="oos"); d2 = d2[d2.time >= H.OOS_START]
        rr = np.log(d2.close).diff().dropna()
        ac1 = rr.autocorr(1); ac2 = rr.autocorr(2)
        # variance ratio 5
        vr = rr.rolling(5).sum().dropna().var() / (5 * rr.var())
        P(f"  {tf}: ac1={ac1:+.3f} ac2={ac2:+.3f} VR5={vr:.2f} n={len(rr)}")
    # daily: gap behaviour (open vs prev close), range-vs-trend classification
    d1 = H.load(s, "D1", split="oos"); d1 = d1[d1.time >= H.OOS_START]
    gap = (d1.open - d1.close.shift()) * 1e4
    fill = ((d1.close - d1.open) * np.sign(-gap)) * 1e4  # positive = moved toward filling
    big = gap.abs() > 5
    P(f"  D1 gaps: |gap|>5p count={int(big.sum())} mean fill-direction move={fill[big].mean():+.1f}p, "
      f"gap filled same day {((((d1.low <= d1.close.shift()) & (gap > 0)) | ((d1.high >= d1.close.shift()) & (gap < 0)))[big]).mean():.0%}")
    # pdh/pdl test stats on H1: how often prior day high is touched, and after touching does close end back inside?
    df1 = H.load(s, "H1", split="oos"); df1 = df1[df1.time >= H.OOS_START]
    t1 = pd.DatetimeIndex(df1.time)
    dd = df1.assign(day=t1.normalize()).groupby("day").agg(h=("high", "max"), l=("low", "min"), o=("open", "first"), c=("close", "last"))
    ph, pl = dd.h.shift(), dd.l.shift()
    touch_h = dd.h >= ph; touch_l = dd.l <= pl
    rev_h = touch_h & (dd.c < ph); rev_l = touch_l & (dd.c > pl)
    both = touch_h & touch_l
    P(f"  PDH touched {touch_h.mean():.0%} of days, close back below PDH after touch {rev_h.sum()/max(touch_h.sum(),1):.0%}; "
      f"PDL touched {touch_l.mean():.0%}, close back above {rev_l.sum()/max(touch_l.sum(),1):.0%}; both {both.mean():.0%}; neither {(~touch_h & ~touch_l).mean():.0%}")
    # range-day vs trend-day: daily range / ATR20, and (close-open)/(range)
    atr20 = (dd.h - dd.l).rolling(20).mean().shift()
    rel = (dd.h - dd.l) / atr20
    body = (dd.c - dd.o).abs() / (dd.h - dd.l)
    P(f"  day range/ATR20: trend days (>1.3) {(rel>1.3).mean():.0%}, tight (<0.7) {(rel<0.7).mean():.0%}; mean body/range={body.mean():.2f}; "
      f"after trend day next-day range/ATR mean={rel.shift(-1)[rel>1.3].mean():.2f}, after tight day {rel.shift(-1)[rel<0.7].mean():.2f}")
    # Asian range (00-09 server) vs London: breakout stats
    ar = df1.assign(day=t1.normalize(), hr=t1.hour)
    asia = ar[ar.hr < 10].groupby("day").agg(ah=("high", "max"), al=("low", "min"))
    rest = ar[ar.hr >= 10].groupby("day").agg(rh=("high", "max"), rl=("low", "min"), rc=("close", "last"))
    j = asia.join(rest, how="inner")
    arng = (j.ah - j.al) * 1e4
    up = j.rh > j.ah; dn = j.rl < j.al
    P(f"  Asian range mean {arng.mean():.1f}p median {arng.median():.1f}p; London+ breaks above {up.mean():.0%}, below {dn.mean():.0%}, both {(up&dn).mean():.0%}; "
      f"close above AH given break-up-only {(j.rc > j.ah)[up & ~dn].mean():.0%}, close below AL given break-dn-only {(j.rc < j.al)[dn & ~up].mean():.0%}")
    # London first hour (10:00 bar) direction vs rest of London (11-18) direction
    first = ar[ar.hr == 10].groupby("day").agg(fo=("open", "first"), fc=("close", "last"))
    later = ar[(ar.hr >= 11) & (ar.hr <= 18)].groupby("day").agg(lo=("open", "first"), lc=("close", "last"))
    jj = first.join(later, how="inner")
    same = np.sign(jj.fc - jj.fo) == np.sign(jj.lc - jj.lo)
    P(f"  10:00 bar direction == 11-18 direction: {same.mean():.0%} (n={len(jj)})")
    # Friday: does Friday close reverse the Mon-Thu move?
    wk = dd.assign(wd=dd.index.dayofweek)
    P(f"  weekday mean daily ret pips: " + " ".join(f"{k}:{v:+.1f}" for k, v in ((dd.c - dd.o) * 1e4).groupby(dd.index.dayofweek).mean().items()))
    # 17:00 and 18:00 server bars (fix-related) mean abs return & reversal of 19-23 vs 15-18
    pre = ar[(ar.hr >= 15) & (ar.hr <= 17)].groupby("day").agg(o=("open", "first"), c=("close", "last"))
    post = ar[(ar.hr >= 18) & (ar.hr <= 22)].groupby("day").agg(o=("open", "first"), c=("close", "last"))
    jf = pre.join(post, lsuffix="_pre", rsuffix="_post", how="inner")
    rev = np.sign(jf.c_pre - jf.o_pre) != np.sign(jf.c_post - jf.o_post)
    P(f"  15-17 move reversed by 18-22: {rev.mean():.0%}; mean 18-22 move given 15-17 up>8p: {((jf.c_post-jf.o_post)*1e4)[(jf.c_pre-jf.o_pre)*1e4>8].mean():+.1f}p, given down<-8p: {((jf.c_post-jf.o_post)*1e4)[(jf.c_pre-jf.o_pre)*1e4<-8].mean():+.1f}p")

open("research/search3/majors/study_out.txt", "w").write("\n".join(out))
