import os, sys, json
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
import pandas as pd, numpy as np
from research.prop import harness as H
from research.search.indicator_screen.strategies import build_index_d1_squeeze as build
print("spec", H._spec().get("US500"), H._spec().get("US30"))
for split in ("is","oos"):
    df = H.load("US500","D1",split=split)
    if split=="oos":
        t=df.time; gaps=t.diff().dt.days; print("big gaps", t[gaps>5].tolist()[:10], gaps[gaps>5].tolist()[:10])
    sigs = build(df, n=20, q=0.25, trend=True)
    res = H.simulate(df, sigs, risk=0.015)
    tr = res["trades"]
    sf = df.attrs.get("score_from")
    if sf is not None: tr = tr[tr.entry_time>=sf]
    tr = tr.copy()
    tr["days"]=(tr.exit_time-tr.entry_time).dt.days
    tr["notional"]=tr.lots*tr.entry*float(H._spec().get("US500",{}).get("contract",1))
    # swap estimate: ~ (5% + 2.5%)/365 of notional per night for longs; shorts ~ -(5%-2.5%) cost too conservatively 2.5%
    rate = np.where(tr.side=="long", 0.075, 0.0)/365
    tr["swap_est"] = -tr.notional*rate*tr.days
    pd.set_option("display.width",250)
    print(split, len(tr)); print(tr[["entry_time","exit_time","side","entry","exit","lots","profit","reason","days","notional","swap_est"]].to_string())
    p=tr.profit.sort_values(ascending=False)
    print("net",tr.profit.sum(),"top1",p.iloc[0] if len(p) else 0,"top2",p.iloc[:2].sum(),"swap_est_total",tr.swap_est.sum(), "net_after_swap", tr.profit.sum()+tr.swap_est.sum())
    print("long share", (tr.side=="long").mean())
