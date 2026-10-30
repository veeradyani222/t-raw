"""Market study + data-quality report for the exotic group.
    python -m research.search3.exotics.study  -> prints markdown, writes study.md
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

os.environ["PROP_OOS"] = "1"
from research.prop import harness as H                      # noqa: E402
from research.search3.exotics import strategies as S        # noqa: E402


def quality(df):
    t = pd.DatetimeIndex(df.time)
    d = pd.DataFrame({"day": t.normalize(), "h": df.high.values, "l": df.low.values,
                      "v": df.tick_volume.values if "tick_volume" in df else 1})
    g = d.groupby("day").agg(h=("h", "max"), l=("l", "min"), n=("h", "size"), v=("v", "sum"))
    rng = g.h - g.l
    flat = rng < 0.05 * rng.median()
    gaps = (t[1:] - t[:-1])
    long_gaps = int((gaps > pd.Timedelta(days=3, hours=12)).sum())
    zero_vol = int((df.tick_volume == 0).sum()) if "tick_volume" in df else 0
    return dict(days=len(g), flat_days=int(flat.sum()), flat_list=list(g.index[flat].strftime("%Y-%m-%d"))[:8],
                long_gaps=long_gaps, zero_vol_bars=zero_vol,
                first=str(t[0].date()), last=str(t[-1].date()), bars=len(df))


def study_symbol(sym):
    out = [f"### {sym}"]
    S.patch_harness()
    h1 = S.clean(H.load(sym, "H1", split="oos"))
    d1 = S.clean(H.load(sym, "D1", split="oos"))
    h1s = h1[h1.time >= H.OOS_START]
    d1s = d1[d1.time >= H.OOS_START]
    q = quality(h1)
    out.append(f"- data H1: {q['bars']} bars {q['first']}..{q['last']}, {q['days']} days; flat days (range<5% of median) {q['flat_days']} {q['flat_list']}; gaps>3.5d {q['long_gaps']}; zero-vol bars {q['zero_vol_bars']}")
    # spread vs ATR
    spec_pt = 1e-5 if sym not in ("USDZAR",) else 1e-5
    bar_sp = (h1s.spread * spec_pt).median() if "spread" in h1s else np.nan
    floor = S.SPREAD_FLOOR[sym]
    a_h1 = np.nanmedian(S.atr(h1s, 14))
    a_d1 = np.nanmedian(S.atr(d1s, 14))
    px = h1s.close.median()
    out.append(f"- price ~{px:.4f}; median bar spread {bar_sp:.5f} ({bar_sp/px*1e4:.1f} bp), floor {floor} ({floor/px*1e4:.1f} bp); H1 ATR {a_h1:.5f} -> spread/ATR(H1) {floor/a_h1:.2f}; D1 ATR {a_d1:.4f} -> spread/ATR(D1) {floor/a_d1:.3f}")
    # hour / weekday returns and vol (H1, scoring window)
    t = pd.DatetimeIndex(h1s.time)
    r = np.log(h1s.close).diff().to_numpy() * 1e4
    hr = pd.DataFrame({"h": t.hour, "wd": t.weekday, "r": r, "rng": (h1s.high - h1s.low).to_numpy() / px * 1e4}).dropna()
    by_h = hr.groupby("h").agg(mean=("r", "mean"), sd=("r", "std"), rng=("rng", "mean"))
    by_h["t"] = by_h["mean"] / by_h["sd"] * np.sqrt(hr.groupby("h").size())
    top = by_h.sort_values("rng", ascending=False).head(5)
    out.append("- busiest server hours (mean H1 range bp): " + ", ".join(f"{h}:{v:.1f}" for h, v in top.rng.items()))
    strong = by_h[abs(by_h.t) > 2.0]
    out.append("- hours with |t|>2 mean return (bp/hr): " + (", ".join(f"{h}:{m:+.2f}(t={tt:.1f})" for h, m, tt in zip(strong.index, strong["mean"], strong.t)) or "none"))
    by_wd = hr.groupby("wd").agg(mean=("r", "sum"), rng=("rng", "mean"))
    out.append("- weekday total drift bp (Mon..Fri): " + ", ".join(f"{m:+.0f}" for m in by_wd["mean"]) + "; mean H1 range bp: " + ", ".join(f"{m:.1f}" for m in by_wd.rng))
    # persistence: autocorr of returns at D1 lag1/lag5, H4 lag1, variance ratio
    rd = np.log(d1s.close).diff().dropna()
    ac1, ac5 = rd.autocorr(1), rd.autocorr(5)
    vr5 = rd.rolling(5).sum().dropna().var() / (5 * rd.var())
    vr20 = rd.rolling(20).sum().dropna().var() / (20 * rd.var())
    # sign persistence: P(sign(ret_{t+1}) == sign(ret_t))
    sp = (np.sign(rd).shift(1) == np.sign(rd)).mean()
    rh = np.log(h1s.close).diff().dropna()
    ach1 = rh.autocorr(1)
    drift = rd.sum() * 1e4
    out.append(f"- D1 return autocorr lag1 {ac1:+.3f}, lag5 {ac5:+.3f}; variance ratio VR(5) {vr5:.2f}, VR(20) {vr20:.2f} (>1 trend, <1 mean-revert); sign persistence {sp:.2f}; H1 autocorr lag1 {ach1:+.3f}; total drift since 2024-10-20 {drift:+.0f} bp")
    # 20-day breakout follow-through: after close > 20d high, next 5d return
    c = d1s.close.to_numpy()
    hh = pd.Series(d1s.high.to_numpy()).rolling(20).max().shift(1).to_numpy()
    ll = pd.Series(d1s.low.to_numpy()).rolling(20).min().shift(1).to_numpy()
    fwd = pd.Series(c).shift(-5).to_numpy() / c - 1
    bu = fwd[(c > hh) & np.isfinite(fwd)]
    bd = fwd[(c < ll) & np.isfinite(fwd)]
    out.append(f"- D1 20-day breakout follow-through (5d fwd, bp): up {np.mean(bu)*1e4 if len(bu) else float('nan'):+.0f} (n={len(bu)}), down {np.mean(bd)*1e4 if len(bd) else float('nan'):+.0f} (n={len(bd)})")
    # gaps: weekend gap size & fill rate
    dd = pd.DatetimeIndex(h1s.time).normalize()
    first = h1s.groupby(dd).first()
    last = h1s.groupby(dd).last()
    gap = (first.open - last.close.shift(1)).dropna()
    is_mon = pd.DatetimeIndex(gap.index).weekday == 0
    gm = gap[is_mon]
    fill = []
    for day, gp in gm.items():
        prevc = last.close.shift(1).loc[day]
        bars = h1s[dd == day]
        fill.append(((bars.low <= prevc).any() if gp > 0 else (bars.high >= prevc).any()))
    out.append(f"- weekend gap: median |gap| {gm.abs().median()/px*1e4:.1f} bp, mean {gm.mean()/px*1e4:+.1f} bp, same-day fill rate {np.mean(fill) if fill else float('nan'):.2f} (n={len(gm)})")
    # volatility regime: ATR percentile spread
    a = S.atr(d1s, 14)
    out.append(f"- D1 ATR p10/p50/p90 bp: {np.nanpercentile(a,10)/px*1e4:.0f}/{np.nanpercentile(a,50)/px*1e4:.0f}/{np.nanpercentile(a,90)/px*1e4:.0f}; biggest day move {rd.abs().max()*1e4:.0f} bp")
    return "\n".join(out), q


if __name__ == "__main__":
    syms = sys.argv[1:] or S.SYMBOLS
    parts = []
    for s in syms:
        try:
            txt, q = study_symbol(s)
        except Exception as e:
            txt = f"### {s}\n- ERROR {e!r}"
        print(txt, flush=True)
        parts.append(txt)
    (os.path.dirname(__file__) and None)
    from pathlib import Path
    Path(__file__).with_name("study.md").write_text("\n\n".join(parts))
