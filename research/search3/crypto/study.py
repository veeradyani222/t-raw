"""Market study + data-quality report for the crypto group (round 3)."""
import os, sys
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H

SYMS = [s for s in ["BTCUSD","ETHUSD","XRPUSD","LTCUSD","SOLUSD","ADAUSD","BNBUSD","DOTUSD"]
        if (H.DATA / f"{s.lower()}-h1.csv").exists()]
print("symbols present:", SYMS)

def quality(sym):
    out = {}
    for tf in ("H1","H4","D1"):
        p = H.DATA / f"{sym.lower()}-{tf.lower()}.csv"
        if not p.exists(): continue
        df = pd.read_csv(p, parse_dates=["time"]).drop_duplicates("time").sort_values("time")
        df = df[df.time >= "2024-01-01"]
        step = {"H1":1,"H4":4,"D1":24}[tf]
        gaps = df.time.diff().dt.total_seconds()/3600
        long_gaps = int((gaps > step*3).sum())
        zero_vol = int((df.tick_volume <= 0).sum())
        d = df.assign(day=df.time.dt.normalize()).groupby("day").agg(h=("high","max"), l=("low","min"))
        rng = d.h - d.l
        flat = int((rng < 0.05*rng.median()).sum())
        out[tf] = dict(bars=len(df), first=str(df.time.iloc[0])[:10], last=str(df.time.iloc[-1])[:16],
                       long_gaps=long_gaps, zero_vol=zero_vol, flat_days=flat, days=len(d))
    return out

for s in SYMS:
    print(s, quality(s))

# market study on H1 2024-10-20..now
for s in SYMS:
    df = H.load(s, "H1", split="oos")
    df = df[df.time >= H.OOS_START].copy()
    r = np.log(df.close/df.close.shift()).fillna(0)
    df["r"] = r; df["hour"] = df.time.dt.hour; df["wd"] = df.time.dt.dayofweek
    df["rng"] = (df.high-df.low)/df.close
    print(f"\n=== {s} H1 {df.time.iloc[0].date()}..{df.time.iloc[-1].date()} bars={len(df)} ===")
    byh = df.groupby("hour").agg(mean_bp=("r", lambda x: 1e4*x.mean()), vol_bp=("r", lambda x: 1e4*x.std()), rng_bp=("rng", lambda x: 1e4*x.mean()))
    print("by hour (EET):"); print(byh.round(1).T.to_string())
    bywd = df.groupby("wd").agg(mean_bp=("r", lambda x: 1e4*x.mean()), vol_bp=("r", lambda x: 1e4*x.std()), rng_bp=("rng", lambda x: 1e4*x.mean()))
    print("by weekday (0=Mon):"); print(bywd.round(1).T.to_string())
    # autocorrelation of returns at various horizons (trend persistence vs MR)
    for tf, k in (("H1",1),("H4",4),("D1",24),("W",168)):
        rr = np.log(df.close/df.close.shift(k)).dropna().iloc[::k]
        ac = rr.autocorr(1)
        print(f"  {tf} return autocorr(1) = {ac:+.3f}  n={len(rr)}")
    # weekend vs weekday: sat/sun returns + vol
    we = df[df.wd>=5]; wk = df[df.wd<5]
    print(f"  weekend hourly vol {1e4*we.r.std():.1f}bp vs weekday {1e4*wk.r.std():.1f}bp; weekend mean {1e4*we.r.mean():+.2f}bp/h weekday {1e4*wk.r.mean():+.2f}bp/h")
    # Monday open effect: Mon 00-08 return conditioned on weekend return
    dd = df.assign(day=df.time.dt.normalize())
    daily = dd.groupby("day").agg(o=("open","first"), c=("close","last"), h=("high","max"), l=("low","min"))
    daily["ret"] = np.log(daily.c/daily.o); daily["wd"] = daily.index.dayofweek
    daily["prev"] = daily.ret.shift()
    print("  daily ret by weekday (bp):", (1e4*daily.groupby("wd").ret.mean()).round(0).to_dict())
    # follow-through: sign(prev day) -> next day mean
    up = daily[daily.prev>0].ret.mean(); dn = daily[daily.prev<0].ret.mean()
    print(f"  next-day mean after up day {1e4*up:+.0f}bp, after down day {1e4*dn:+.0f}bp")
    # multi-day breakout: close > 20d high -> next 5d return
    daily["h20"] = daily.h.rolling(20).max().shift(); daily["l20"] = daily.l.rolling(20).min().shift()
    daily["fwd5"] = np.log(daily.c.shift(-5)/daily.c)
    bo = daily[daily.c>daily.h20].fwd5; bd = daily[daily.c<daily.l20].fwd5
    print(f"  20d breakout up -> 5d fwd {1e4*bo.mean():+.0f}bp (n={bo.count()}), breakdown -> {1e4*bd.mean():+.0f}bp (n={bd.count()})")
    # vol regime: range contraction (5d avg range / 20d) -> next 5d abs move
    daily["rng"] = (daily.h-daily.l)/daily.c
    daily["cmp"] = daily.rng.rolling(5).mean()/daily.rng.rolling(20).mean()
    lo = daily[daily.cmp<0.7]; hi = daily[daily.cmp>1.3]
    print(f"  after compression(<0.7) |5d fwd| {1e4*lo.fwd5.abs().mean():.0f}bp vs expansion(>1.3) {1e4*hi.fwd5.abs().mean():.0f}bp")
    # US session momentum: return 15-18 EET (NY open) vs follow through 18-24
    a = df[(df.hour>=16)&(df.hour<=18)].groupby(df.time.dt.normalize()).r.sum()
    b = df[(df.hour>=19)&(df.hour<=23)].groupby(df.time.dt.normalize()).r.sum()
    j = pd.concat([a,b],axis=1,keys=["ny","late"]).dropna()
    print(f"  corr(NY open 16-18 ret, late 19-23 ret) = {j.ny.corr(j.late):+.3f}; Asia(02-09) vs London(10-15) corr = ", end="")
    a2 = df[(df.hour>=2)&(df.hour<=9)].groupby(df.time.dt.normalize()).r.sum()
    b2 = df[(df.hour>=10)&(df.hour<=15)].groupby(df.time.dt.normalize()).r.sum()
    j2 = pd.concat([a2,b2],axis=1,keys=["a","b"]).dropna(); print(f"{j2.a.corr(j2.b):+.3f}")

# BTC-ETH lead/lag
if "BTCUSD" in SYMS and "ETHUSD" in SYMS:
    b = H.load("BTCUSD","H1",split="oos"); e = H.load("ETHUSD","H1",split="oos")
    m = pd.merge(b[["time","close"]], e[["time","close"]], on="time", suffixes=("_b","_e"))
    m = m[m.time>=H.OOS_START]
    rb = np.log(m.close_b/m.close_b.shift()); re = np.log(m.close_e/m.close_e.shift())
    print("\nBTC-ETH H1: contemporaneous corr", round(rb.corr(re),3), "BTC(t-1)->ETH(t)", round(rb.shift().corr(re),3), "ETH(t-1)->BTC(t)", round(re.shift().corr(rb),3))
    rel = np.log(m.close_e/m.close_b); rel5d = rel.diff(120)
    fwd = np.log(m.close_e.shift(-24)/m.close_e)
    print("ETH/BTC 5d rel strength vs ETH next-24h ret corr:", round(rel5d.corr(fwd),3))
