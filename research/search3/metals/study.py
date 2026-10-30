"""Market study + data quality for XAUUSD XAGUSD XPTUSD XPDUSD (scoring window 2024-10-20..now)."""
import os, sys
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H

SYMS = ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"]
for sym in SYMS:
    print("=" * 70); print(sym)
    d1 = H.load(sym, "D1", split="all")
    d1 = d1[d1.time >= "2024-10-20"]
    rng = d1.high - d1.low
    med = rng.median()
    flat = d1[rng < 0.05 * med]
    print(f"D1 bars {len(d1)}  flat days(range<5% median) {len(flat)}", list(flat.time.dt.date)[:10])
    print("zero tick_volume D1:", int((d1.tick_volume == 0).sum()))
    h1 = H.load(sym, "H1", split="all")
    h1 = h1[h1.time >= "2024-10-20"].reset_index(drop=True)
    gaps = h1.time.diff().dt.total_seconds() / 3600
    big = h1[gaps > 3]
    print(f"H1 bars {len(h1)} gaps>3h {len(big)} (weekend expected ~{len(h1)//120})  gaps>60h: {int((gaps>60).sum())}  zero-vol H1: {int((h1.tick_volume==0).sum())}")
    print("first/last", h1.time.iloc[0], h1.time.iloc[-1])
    print("median spread pts", h1.spread.median(), "price", h1.close.median(), "spread%", 100*h1.spread.median()*{'XAUUSD':0.01,'XAGUSD':0.001,'XPTUSD':0.01,'XPDUSD':0.01}[sym]/h1.close.median())
    # hourly stats
    h1["ret"] = np.log(h1.close / h1.open)
    h1["rng"] = (h1.high - h1.low) / h1.close * 1e4
    h1["hour"] = h1.time.dt.hour; h1["wd"] = h1.time.dt.weekday
    g = h1.groupby("hour").agg(ret_bp=("ret", lambda x: x.mean()*1e4), rng_bp=("rng", "mean"), n=("ret", "size"))
    print("by hour (mean ret bp, mean range bp):"); print(g.round(1).T.to_string())
    g = h1.groupby("wd").agg(ret_bp=("ret", lambda x: x.sum()*1e4), rng_bp=("rng", "mean"))
    print("by weekday (sum ret bp, mean range bp):"); print(g.round(1).T.to_string())
    # intraday autocorrelation: does hour-h return predict next hour?
    for tf, lag_label in (("H1", "1 bar"), ("H4", "1 bar"), ("D1", "1 bar")):
        d = H.load(sym, tf, split="all"); d = d[d.time >= "2024-10-20"]
        r = np.log(d.close).diff().dropna()
        ac1 = r.autocorr(1); ac2 = r.autocorr(2)
        # variance ratio 5
        vr = (r.rolling(5).sum().dropna().var() / (5 * r.var()))
        print(f"{tf}: ac1 {ac1:+.3f} ac2 {ac2:+.3f} VR5 {vr:.2f}  (VR>1 trend, <1 mean-rev) n={len(r)}")
    # session returns: Asia 1-9, London 9-15, NY 15-23 (server EET)
    def sess(h):
        return "asia" if 1 <= h < 9 else ("london" if 9 <= h < 15 else "ny")
    h1["sess"] = h1.hour.map(sess)
    s = h1.groupby([h1.time.dt.date, "sess"]).ret.sum().unstack()
    print("session mean ret bp:", (s.mean()*1e4).round(1).to_dict(), " corr asia->london", round(s.asia.corr(s.london),3), " london->ny", round(s.london.corr(s.ny),3), " asia->rest", round(s.asia.corr(s.london+s.ny),3))
    # gap: Monday open vs Friday close
    d = H.load(sym, "D1", split="all"); d = d[d.time >= "2024-10-20"].reset_index(drop=True)
    gap = np.log(d.open / d.close.shift(1)); day = np.log(d.close / d.open)
    print("overnight gap bp mean", round(gap.mean()*1e4,1), "std", round(gap.std()*1e4,1), " corr gap->day", round(gap.corr(day),3))
    # prior-day high/low test frequency
    pdh = d.high.shift(1); pdl = d.low.shift(1)
    print("touch PDH %", round((d.high >= pdh).mean()*100,1), "touch PDL %", round((d.low <= pdl).mean()*100,1), "both", round(((d.high>=pdh)&(d.low<=pdl)).mean()*100,1), "close outside PD range %", round(((d.close>pdh)|(d.close<pdl)).mean()*100,1))
    # fix behaviour: return 11-12:30 vs 12:30-14 ; 15:30-17 vs 17-18:30 (use M30)
    m = H.load(sym, "M30", split="all"); m = m[m.time >= "2024-10-20"].reset_index(drop=True)
    m["hm"] = m.time.dt.hour * 100 + m.time.dt.minute
    m["ret"] = np.log(m.close/m.open)
    m["date"] = m.time.dt.date
    def win(a, b):
        return m[(m.hm >= a) & (m.hm < b)].groupby("date").ret.sum()
    pre_am, post_am = win(1100, 1230), win(1230, 1400)
    pre_pm, post_pm = win(1530, 1700), win(1700, 1830)
    print(f"AM fix: pre mean {pre_am.mean()*1e4:+.1f}bp post {post_am.mean()*1e4:+.1f}bp corr {pre_am.corr(post_am):+.3f}")
    print(f"PM fix: pre mean {pre_pm.mean()*1e4:+.1f}bp post {post_pm.mean()*1e4:+.1f}bp corr {pre_pm.corr(post_pm):+.3f}")
    # asian range breakout: range 1:00-9:00, break during london?
    asia = m[(m.hm >= 100) & (m.hm < 900)].groupby("date").agg(ah=("high","max"), al=("low","min"))
    rest = m[(m.hm >= 900)].groupby("date").agg(rh=("high","max"), rl=("low","min"), c=("close","last"))
    j = asia.join(rest, how="inner")
    j["ar"] = j.ah - j.al
    print("asia range / day-range med", round((j.ar / (np.maximum(j.rh,j.ah)-np.minimum(j.rl,j.al))).median(),2), " break up %", round((j.rh>j.ah).mean()*100,1), "break dn %", round((j.rl<j.al).mean()*100,1), " both %", round(((j.rh>j.ah)&(j.rl<j.al)).mean()*100,1))
    up_only = j[(j.rh>j.ah)&~(j.rl<j.al)]; dn_only = j[(j.rl<j.al)&~(j.rh>j.ah)]
    print("  up-only days close above asia high %", round((up_only.c>up_only.ah).mean()*100,1), "dn-only days close below asia low %", round((dn_only.c<dn_only.al).mean()*100,1))
