import os, sys
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.published_research import strategies as S

def run(df, sigs, risk=0.015, start=None):
    r = H.simulate(df, sigs, risk=risk)
    t = r["trades"]
    if start is not None: t = t[t.entry_time >= start]
    return t

for split in ("is", "oos"):
    df = H.load("US30", "H1", split=split)
    start = df.attrs.get("score_from")
    sigs = S.build_equity_calendar(df, tom_days_before=0)
    # tag components
    comp = {}
    for nm, p in (("fomc", S.build_pre_fomc(df, "long", sl_datr=1.5)), ("hol", S.build_pre_holiday(df, sl_datr=1.5)),
                  ("tom", S.build_turn_of_month(df, days_before=0, hold_days=4, sl_datr=1.5))):
        for i, e in enumerate(p):
            if e is not None and i not in comp: comp[i] = nm
    times = pd.DatetimeIndex(df.time)
    t = run(df, sigs, start=start).copy()
    idx = {ts: k for k, ts in enumerate(times)}
    t["comp"] = [comp.get(idx[x]) for x in t.entry_time]
    t["nights"] = [(pd.Timestamp(b).normalize() - pd.Timestamp(a).normalize()).days for a, b in zip(t.entry_time, t.exit_time)]
    t["notional"] = t.lots * t.entry  # contract 1?
    print(f"\n==== {split}: trades {len(t)} net {t.profit.sum():.0f}")
    print(t.groupby("comp").profit.agg(["count", "sum", "mean"]))
    print("reasons", t.reason.value_counts().to_dict())
    s = t.profit.sort_values(ascending=False)
    print("top5 trades", s.head(5).round(0).tolist(), "net ex top1", round(s.iloc[1:].sum()), "ex top3", round(s.iloc[3:].sum()))
    print("mean lots", t.lots.mean().round(3), "mean entry", t.entry.mean().round(0), "mean nights", t.nights.mean().round(2), "total nights", t.nights.sum())
    # swap estimate: annual financing (rate + markup) on notional, per calendar night
    spec = H._spec().get("US30", {}); contract = float(spec.get("contract", 1))
    print("contract", contract)
    for rate in (0.05, 0.07, 0.08):
        cost = (t.lots * contract * t.entry * rate / 365 * t.nights).sum()
        print(f"  swap@{rate:.0%}/yr est ${cost:.0f}  -> net after swap {t.profit.sum()-cost:.0f}")
    if split == "oos":
        print(t[["entry_time", "exit_time", "comp", "lots", "entry", "exit", "profit", "reason"]].sort_values("profit").tail(6).to_string())
        print(t[t.entry_time.dt.to_period("M") == pd.Period("2024-11")][["entry_time","exit_time","comp","profit","reason"]])
    # spread at entry hour
    sp = df.spread.groupby(times.hour).median()
    print("median bar spread pts by hour 20-23,0:", sp.reindex([20,21,22,23,0]).to_dict(), "point", spec.get("point"))
    # placebo on same split
    pl = []
    for off in range(8):
        tp = run(df, S.build_control_long(df, every=8, offset=off, hold_days=4, entry_hour=22, sl_datr=1.5), start=start)
        pl.append(tp.profit.sum())
    print("placebo every8 nets:", np.round(pl).tolist(), "mean", round(np.mean(pl)))
