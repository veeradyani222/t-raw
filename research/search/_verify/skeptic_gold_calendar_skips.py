import os, sys, math
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
os.environ["PROP_OOS"] = "1"
import pandas as pd
from research.prop import harness as H
import research.search.published_research.strategies as S
df=H.load("XAUUSD","H1",split="oos")
sig=S.build_gold_calendar(df,tom_days_before=0,tom_hold=4,fomc_sl=1.5)
tr=H.simulate(df,sig,risk=0.02)["trades"]; et=set(tr.entry_time)
for i,e in enumerate(sig):
    if e is None or df.time.iloc[i]<pd.Timestamp("2024-01-01") or df.time.iloc[i] in et: continue
    c=df.close.iloc[i]; lpl=(abs(c+0.3-e.sl))*100+14
    print(df.time.iloc[i], "stop $", round(c-e.sl,1), "lots wanted", round(200/lpl,4))
# months with no TOM signal at all
t=pd.DatetimeIndex(df.time); print(df[(t>="2025-11-26")&(t<"2025-12-02")].time.dt.strftime("%m-%d %H").tolist()[-40:])
