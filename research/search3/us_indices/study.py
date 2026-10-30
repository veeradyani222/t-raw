"""Market study + data-quality report for US30/US500/USTEC(/US2000).
Run: PYTHONPATH=. python research/search3/us_indices/study.py
"""
import os, sys
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H

SYMS = [s for s in ("US30", "US500", "USTEC", "US2000") if (H.DATA / f"{s.lower()}-h1.csv").exists()]

FOMC = ["2019-01-30","2019-03-20","2019-05-01","2019-06-19","2019-07-31","2019-09-18","2019-10-30","2019-12-11",
        "2020-01-29","2020-03-03","2020-03-15","2020-04-29","2020-06-10","2020-07-29","2020-09-16","2020-11-05","2020-12-16",
        "2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22","2021-11-03","2021-12-15",
        "2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14",
        "2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13",
        "2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18",
        "2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30","2025-09-17","2025-10-29","2025-12-10",
        "2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16","2026-10-28","2026-12-09"]


def dq(sym, tf):
    df = pd.read_csv(H.DATA / f"{sym.lower()}-{tf.lower()}.csv", parse_dates=["time"])
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    d = df.assign(day=df.time.dt.normalize())
    rng = d.groupby("day").apply(lambda g: g.high.max() - g.low.min())
    med = rng.rolling(60, min_periods=20).median()
    flat = rng[(rng < 0.05 * med)]
    gaps = df.time.diff()
    big = gaps[gaps > pd.Timedelta(hours=72)]
    zero = int((df.tick_volume == 0).sum())
    dup_oc = int(((df.open == df.high) & (df.high == df.low) & (df.low == df.close)).sum())
    return dict(sym=sym, tf=tf, bars=len(df), first=str(df.time.iloc[0])[:10], last=str(df.time.iloc[-1])[:16],
                flat_days=len(flat), flat_list=[str(x)[:10] for x in flat.index[:10]],
                gaps_gt72h=len(big), gap_list=[(str(df.time.iloc[i-1])[:10], str(df.time.iloc[i])[:10], str(g)) for i, g in big.items()][:8],
                zero_vol=zero, ohlc_equal=dup_oc)


def study(sym):
    df = H.load(sym, "H1", split="all")
    df = df[df.time >= "2022-01-01"].reset_index(drop=True)
    df["ret"] = np.log(df.close / df.close.shift())
    df["hour"] = df.time.dt.hour; df["dow"] = df.time.dt.dayofweek
    out = [f"\n=== {sym} H1 (2022-01 .. {str(df.time.iloc[-1])[:10]}) ==="]
    g = df.groupby("hour")["ret"]
    tab = pd.DataFrame({"mean_bp": g.mean() * 1e4, "std_bp": g.std() * 1e4, "n": g.size(),
                        "t": g.mean() / g.std() * np.sqrt(g.size())})
    out.append("Return by server hour (bp, bar close-to-close):\n" + tab.round(2).to_string())
    g = df.groupby("dow")["ret"]
    out.append("By weekday:\n" + pd.DataFrame({"mean_bp": g.mean() * 1e4, "std_bp": g.std() * 1e4, "n": g.size()}).round(2).to_string())
    d1 = H.load(sym, "D1", split="all"); d1 = d1[d1.time >= "2019-01-01"].reset_index(drop=True)
    dd = d1.assign(ret=np.log(d1.close / d1.close.shift()))
    m30 = pd.read_csv(H.DATA / f"{sym.lower()}-m30.csv", parse_dates=["time"]).drop_duplicates("time").sort_values("time")
    m30 = m30[m30.time >= "2022-01-01"].reset_index(drop=True)
    m30["day"] = m30.time.dt.normalize(); m30["hm"] = m30.time.dt.hour * 100 + m30.time.dt.minute
    rows = []
    for day, g in m30.groupby("day"):
        g = g.set_index("hm")
        if 1630 not in g.index or 2230 not in g.index or 1600 not in g.index:
            continue
        o = g.loc[1630, "open"]; c = g.loc[2230, "close"]; fh = g.loc[1700, "close"] if 1700 in g.index else np.nan
        lh = g.loc[2200, "open"] if 2200 in g.index else np.nan
        pre = g.loc[1600, "close"]
        sub = g.loc[1630:2230]
        rows.append(dict(day=day, open=o, close=c, fh=fh, lh=lh, pre=pre,
                         or_hi=g.loc[1630, "high"], or_lo=g.loc[1630, "low"],
                         hi=sub.high.max(), lo=sub.low.min()))
    s = pd.DataFrame(rows).set_index("day")
    s["prev_close"] = s.close.shift()
    s["gap"] = s.open / s.prev_close - 1
    s["overnight"] = s.open / s.prev_close - 1
    s["cash"] = s.close / s.open - 1
    s["first_h"] = s.fh / s.open - 1
    s["mid"] = s.lh / s.fh - 1
    s["last_h"] = s.close / s.lh - 1
    out.append("Session returns (bp/day, mean, std, t):")
    for k in ("overnight", "cash", "first_h", "mid", "last_h"):
        x = s[k].dropna(); out.append(f"  {k:<10} mean {x.mean()*1e4:6.2f}  std {x.std()*1e4:6.1f}  t {x.mean()/x.std()*np.sqrt(len(x)):5.2f}  n {len(x)}")
    gp = s.dropna(subset=["gap"])
    up = gp[gp.gap > 0.002]; dn = gp[gp.gap < -0.002]
    fill_up = (up.lo <= up.prev_close).mean(); fill_dn = (dn.hi >= dn.prev_close).mean()
    out.append(f"Gap >0.2%: n {len(up)} filled same day {fill_up:.0%}, cash ret mean {up.cash.mean()*1e4:.1f}bp | gap <-0.2%: n {len(dn)} filled {fill_dn:.0%}, cash ret mean {dn.cash.mean()*1e4:.1f}bp")
    fh = s.dropna(subset=["first_h"])
    same = ((fh.close - fh.fh) * np.sign(fh.first_h) > 0).mean()
    out.append(f"First-hour direction continues to close: {same:.0%} of days (n {len(fh)}); corr(first_h, rest) {np.corrcoef(fh.first_h, (fh.close/fh.fh-1))[0,1]:.3f}")
    brk_up = (s.close > s.or_hi).mean(); brk_dn = (s.close < s.or_lo).mean()
    out.append(f"Close above OR30 high {brk_up:.0%}, below OR30 low {brk_dn:.0%}; OR30 range / day range median {((s.or_hi-s.or_lo)/(s.hi-s.lo)).median():.2f}")
    r = dd.ret.dropna()
    out.append(f"D1 autocorr lag1 {r.autocorr(1):.3f} lag2 {r.autocorr(2):.3f}; H1 autocorr lag1 {df.ret.autocorr(1):.3f}")
    for k in (2, 5, 10, 20):
        vr = r.rolling(k).sum().var() / (k * r.var())
        out.append(f"  D1 variance ratio {k}d: {vr:.2f}")
    hr = df.ret.dropna()
    for k in (2, 4, 8, 24):
        vr = hr.rolling(k).sum().var() / (k * hr.var())
        out.append(f"  H1 variance ratio {k}h: {vr:.2f}")
    dd["lo20"] = dd.low.rolling(20).min().shift(); dd["hi20"] = dd.high.rolling(20).max().shift()
    dd["sma200"] = dd.close.rolling(200).mean()
    dd["fwd5"] = np.log(dd.close.shift(-5) / dd.close); dd["fwd1"] = np.log(dd.close.shift(-1) / dd.close)
    for lab, m in (("close<20d low", dd.close < dd.lo20), ("close>20d high", dd.close > dd.hi20),
                   ("3 down closes", (dd.ret < 0) & (dd.ret.shift() < 0) & (dd.ret.shift(2) < 0)),
                   ("3 down & >sma200", (dd.ret < 0) & (dd.ret.shift() < 0) & (dd.ret.shift(2) < 0) & (dd.close > dd.sma200)),
                   ("below sma200", dd.close < dd.sma200), ("above sma200", dd.close > dd.sma200)):
        x = dd[m]
        out.append(f"  {lab:<20} n {len(x):4d} fwd1 {x.fwd1.mean()*1e4:6.1f}bp fwd5 {x.fwd5.mean()*1e4:6.1f}bp")
    dd["ym"] = dd.time.dt.to_period("M")
    dd["tdm"] = dd.groupby("ym").cumcount() + 1
    dd["tdm_end"] = dd.groupby("ym")["tdm"].transform("max") - dd.tdm
    tom = pd.concat([dd[dd.tdm_end <= 1].assign(k=lambda x: -x.tdm_end - 1), dd[dd.tdm <= 4].assign(k=lambda x: x.tdm)])
    out.append("Turn of month (day k, -2..-1 = last 2, 1..4 = first 4): mean next-day ret bp\n" +
               tom.groupby("k").fwd1.agg(["mean", "count"]).assign(mean=lambda x: x["mean"] * 1e4).round(1).to_string())
    out.append("D1 return by weekday (bp): " + str((dd.groupby(dd.time.dt.dayofweek).ret.mean() * 1e4).round(1).to_dict()))
    dd["dom"] = dd.time.dt.day; dd["dow"] = dd.time.dt.dayofweek
    third_fri = dd[(dd.dow == 4) & (dd.dom >= 15) & (dd.dom <= 21)].time
    wk = dd.time.dt.to_period("W")
    opex_weeks = set(third_fri.dt.to_period("W"))
    is_opex = wk.isin(opex_weeks); is_post = (wk - 1).isin(opex_weeks)
    out.append(f"OpEx week mean day ret {dd[is_opex].ret.mean()*1e4:.1f}bp (n {is_opex.sum()}), week after {dd[is_post].ret.mean()*1e4:.1f}bp, other {dd[~is_opex & ~is_post].ret.mean()*1e4:.1f}bp")
    fomc = pd.to_datetime(FOMC)
    f = dd[dd.time.dt.normalize().isin(fomc)]
    pre = dd[(dd.time.dt.normalize() + pd.Timedelta(days=1)).isin(fomc)]
    out.append(f"FOMC day ret {f.ret.mean()*1e4:.1f}bp (n {len(f)}), day before {pre.ret.mean()*1e4:.1f}bp, FOMC fwd1 {f.fwd1.mean()*1e4:.1f}bp")
    dd["atr"] = (dd.high - dd.low).rolling(14).mean() / dd.close
    hi = dd.atr > dd.atr.rolling(100).median() * 1.3
    out.append(f"High-vol regime (ATR14 > 1.3x 100d median): n {hi.sum()}, fwd1 {dd[hi].fwd1.mean()*1e4:.1f}bp, fwd5 {dd[hi].fwd5.mean()*1e4:.1f}bp; low-vol fwd5 {dd[~hi].fwd5.mean()*1e4:.1f}bp")
    return "\n".join(out)


if __name__ == "__main__":
    print("DATA QUALITY")
    for s in SYMS:
        for tf in ("M30", "H1", "H4", "D1"):
            print(dq(s, tf))
    for s in SYMS:
        print(study(s))
