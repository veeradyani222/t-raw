import sys, numpy as np, pandas as pd
from research.search3.oil_gas import common as C
from research.prop import harness as H
for sym in sys.argv[1:]:
    for tf in ("M30","H1","H4","D1"):
        try:
            raw = H.load(sym, tf, split="oos"); rep = {}; df = C.clean(raw, rep)
        except FileNotFoundError:
            print(sym, tf, "missing"); continue
        print(f"\n== {sym} {tf}: {rep}  span {raw.time.min()} -> {raw.time.max()}  spread median pts {raw.spread.median():.0f} -> price {raw.spread.median()*H._spec()[sym]['point']:.4f}")
    df = C.clean(H.load(sym, "H1", split="oos"), {})
    d = df[df.time >= "2024-10-20"].copy()
    d["ret"] = np.log(d.close / d.close.shift()); d["rng"] = (d.high - d.low) / d.close
    d["hr"] = d.time.dt.hour; d["wd"] = d.time.dt.weekday
    print("hours present:", sorted(d.hr.unique()))
    g = d.groupby("hr").agg(ret_bp=("ret", lambda x: x.mean() * 1e4), rng_pct=("rng", lambda x: x.mean() * 100), vol=("tick_volume", "mean"), n=("ret", "size"))
    print(g.round(2).to_string())
    print("weekday ret bp:", (d.groupby("wd").ret.sum() / d.groupby("wd").ret.size() * 1e4).round(1).to_dict())
    print("day of week total move (sum ret bp over window):", (d.groupby("wd").ret.sum() * 1e4).round(0).to_dict())
    # intraday autocorr: day-open->hour h move vs h->close
    day = d.time.dt.normalize(); d["dopen"] = d.groupby(day).open.transform("first"); d["dclose"] = d.groupby(day).close.transform("last")
    for h in (10, 16, 17, 18, 19, 20, 21):
        x = d[d.hr == h]; a = np.log(x.close / x.dopen); b = np.log(x.dclose / x.close)
        print(f" at {h:02d}: corr(open->now, now->close) = {a.corr(b):.3f}  n={len(x)}")
    # Wed 17:00 bar vs rest of day
    for wd_, lab in ((2, "Wed"), (3, "Thu")):
        x = d[(d.wd == wd_) & (d.hr == 17)]; a = np.log(x.close / x.open); b = np.log(x.dclose / x.close)
        print(f" {lab} 17:00 bar vs 18->close corr {a.corr(b):.3f}, mean abs 17h bar {a.abs().mean()*1e4:.0f}bp vs other hours {d[d.wd==wd_].ret.abs().mean()*1e4:.0f}bp n={len(x)}")
    # gap stats at first bar of day
    f = d[day != day.shift()]; pc = d.close.shift()[f.index]
    gap = (f.open - pc) / pc
    print(f" day-first bar hour {f.hr.mode().iat[0]}, mean |gap| {gap.abs().mean()*1e4:.0f}bp, gap>20bp count {(gap.abs()>0.002).sum()}")
