"""Market study for European indices (server time = EET)."""
import sys
sys.path.insert(0, ".")
from research.search3.europe_indices.common import *

pd.set_option("display.width", 200, "display.max_columns", 30)
for sym in SYMBOLS + ["ESP35"]:
    for tf in ("M30", "H1", "H4", "D1"):
        try:
            raw = H.load(sym, tf, split="oos")
        except FileNotFoundError:
            print(sym, tf, "MISSING"); continue
        m, q = quality_mask(raw)
        print(f"QUALITY {sym} {tf}: {q}  span {raw.time.iloc[0].date()}..{raw.time.iloc[-1].date()}")
    df = load(sym, "H1")
    df = df[df.time >= "2024-10-20"].copy()
    t = pd.DatetimeIndex(df.time)
    df["hr"] = t.hour; df["wd"] = t.weekday; df["day"] = t.normalize()
    df["r"] = np.log(df.close / df.open) * 1e4   # bps, bar return
    df["hl"] = (df.high - df.low) / df.close * 1e4
    print(f"\n=== {sym} H1 bars by hour (count, mean bps, std bps, range bps) ===")
    g = df.groupby("hr").agg(n=("r", "size"), mean=("r", "mean"), std=("r", "std"), rng=("hl", "mean")).round(2)
    print(g.T.to_string())
    print("by weekday:", df.groupby("wd")["r"].agg(["mean", "std", "size"]).round(2).T.to_string())
    # intraday autocorrelation: next-bar vs this-bar by hour
    df["r_next"] = df.r.shift(-1)
    ac = df.groupby("hr").apply(lambda g: g.r.corr(g.r_next)).round(3)
    print("lag1 corr by hour:", ac.to_dict())
    # 10:00 bar vs 11:00-13:00 return; 16:00/17:00 bar vs rest of day
    d = df.pivot_table(index="day", columns="hr", values="r", aggfunc="sum")
    def corr(a, bs):
        if a in d and all(b in d for b in bs):
            x = d[a]; y = d[bs].sum(axis=1)
            return round(x.corr(y), 3)
    print("corr(10h, 11-12h):", corr(10, [11, 12]), " corr(10h, 11-17h):", corr(10, list(range(11, 18))),
          " corr(16h, 17-18h):", corr(16, [17, 18]), " corr(17h, 18-22h):", corr(17, [18, 19, 20, 21, 22]),
          " corr(10-11h,12-18h):", d[[10, 11]].sum(axis=1).corr(d[list(range(12, 19))].sum(axis=1)).round(3) if 10 in d else None)
    # session legs
    legs = {"overnight 23-9": list(range(0, 10)) + [23], "open 10-11": [10, 11], "mid 12-15": [12, 13, 14, 15],
            "us 16-18": [16, 17, 18], "late 19-22": [19, 20, 21, 22]}
    for k, hs in legs.items():
        hs = [h for h in hs if h in d]
        s = d[hs].sum(axis=1)
        print(f"  {k:<16} mean {s.mean():6.1f} bps  std {s.std():6.1f}  n {s.notna().sum()}")
    # gaps: cash open (10:00 bar open) vs previous day's 18:00 bar close (cash close 18:30)
    dd = load(sym, "D1"); dd = dd[dd.time >= "2024-10-20"]
    atr = (dd.high - dd.low).rolling(20).mean()
    # daily autocorr
    dr = np.log(dd.close / dd.close.shift())
    print("daily lag1 autocorr:", round(dr.autocorr(1), 3), " lag2:", round(dr.autocorr(2), 3),
          " weekly(5d) vs next 5d:", round(dr.rolling(5).sum().corr(dr.rolling(5).sum().shift(-5)), 3))
    # gap at cash open from H1
    h = load(sym, "H1"); h = h[h.time >= "2024-10-20"]
    th = pd.DatetimeIndex(h.time)
    cash = h[(th.hour >= 10) & (th.hour <= 18)]
    tc = pd.DatetimeIndex(cash.time)
    op = cash.groupby(tc.normalize()).first(); cl = cash.groupby(tc.normalize()).last()
    gap = (op.open - cl.close.shift()) / cl.close.shift() * 1e4
    day_ret = (cl.close - op.open) / op.open * 1e4
    print("cash gap bps: mean", round(gap.mean(), 1), "std", round(gap.std(), 1), " corr(gap, open->close):", round(gap.corr(day_ret), 3),
          " |gap|>30bps days:", int((gap.abs() > 30).sum()), "of", len(gap))
    big = gap.abs() > 20
    print("  big gap: mean cash-session ret in gap direction:", round((np.sign(gap[big]) * day_ret[big]).mean(), 1), "bps, n", int(big.sum()))
