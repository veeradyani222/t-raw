import os, sys
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.published_research import strategies as S
for split in ("is","oos"):
    df = H.load("US30","H1",split=split); st = df.attrs.get("score_from")
    def T(sigs):
        t = H.simulate(df, sigs, risk=0.015)["trades"]
        return t[t.entry_time>=st] if st is not None else t
    t = T(S.build_equity_calendar(df, tom_days_before=0))
    print(split, "strategy per-trade $", round(t.profit.mean(),1), "R", round(t.r.mean(),3), "n", len(t))
    rs=[]
    for off in range(8):
        tp = T(S.build_control_long(df, every=8, offset=off, hold_days=4, entry_hour=22, sl_datr=1.5))
        rs.append((len(tp), round(tp.profit.mean(),1), round(tp.r.mean(),3)))
    print(split, "placebo (n, $/trade, R/trade):", rs)
    # TOM-only and non-TOM
    for nm, sg in (("tom_only", S.build_equity_calendar(df, tom_days_before=0, holiday=False, fomc=False)),
                   ("fomc+hol", S.build_equity_calendar(df, tom=False))):
        x = T(sg); print(split, nm, len(x), round(x.profit.sum()), "R/trade", round(x.r.mean(),3))
    if split=="oos":
        x = T(S.build_equity_calendar(df, tom_days_before=1))
        print("oos default tom_days_before=1:", len(x), round(x.profit.sum()))
