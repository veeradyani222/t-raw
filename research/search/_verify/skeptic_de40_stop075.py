import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.breakout.strategies import build_de40_xetra_orb as build
P = {"rs":10,"re":10.5,"te":12.5,"exit_h":18,"sl_frac":0.75,"trend":"d","min_rng":0.1,"tp_r":None}
df = H.load("DE40","M30",split="oos")
t = pd.DatetimeIndex(df.time)
o = df[t>=pd.Timestamp("2024-01-01")]
print("oos bars", len(o), o.time.min(), o.time.max())
gaps = o.time.diff()
print("big gaps:\n", o.loc[gaps>pd.Timedelta(days=4),"time"].to_frame().assign(gap=gaps[gaps>pd.Timedelta(days=4)]))
print("bars per month:\n", o.groupby(o.time.dt.to_period("M")).size().to_string())
hrs = pd.DatetimeIndex(o.time)
print("first bar hour per day dist:", pd.Series(hrs).groupby(hrs.normalize()).min().dt.hour.value_counts().head())
print("last bar hour dist:", pd.Series(hrs).groupby(hrs.normalize()).max().dt.strftime("%H:%M").value_counts().head())
# tick volume profile by hour to check where Xetra open is (volume spike)
vol = o.groupby(hrs.strftime("%H:%M"))["tick_volume"].median()
print("median tick vol by bar time:\n", vol.loc["08:00":"12:00"].to_string())
for y in (2024,2025,2026):
    oo=o[o.time.dt.year==y]; hh=pd.DatetimeIndex(oo.time)
    v=oo.groupby(hh.strftime("%H:%M"))["tick_volume"].median()
    print(y, v.loc["09:00":"11:00"].round().to_dict())
print("spread median by time 10:00-12:30 (points):", o.groupby(hrs.strftime("%H:%M"))["spread"].median().loc["10:00":"12:30"].to_dict())
sigs = build(df, **P)
sim = H.simulate(df, sigs, risk=0.005)
tr = sim["trades"]; tr = tr[tr.entry_time>=pd.Timestamp("2024-01-01")]
print("trades", len(tr), "net", tr.profit.sum().round(1), "winrate", (tr.profit>0).mean().round(3))
print("reasons", tr.reason.value_counts().to_dict())
s = tr.profit.sort_values(ascending=False)
print("top5 trades sum", s.head(5).sum().round(1), "top10", s.head(10).sum().round(1))
print(tr.sort_values("profit",ascending=False).head(8)[["entry_time","side","entry","exit","sl0","lots","profit","r","reason"]].to_string())
print("side split", tr.groupby("side").profit.agg(["count","sum"]).to_string())
print("by year", tr.groupby(tr.entry_time.dt.year).profit.agg(["count","sum"]).to_string())
print("mean R", tr.r.mean().round(3), "median lots", tr.lots.median(), "risk_usd vs 50: ", (tr.lots).describe().to_dict())
# realized risk per trade
# slippage sensitivity: add extra adverse points per side
for extra in (1,2,3,5):
    adj = tr.profit - 2*extra*tr.lots*1.0*1.08
    print(f"extra slip {extra}pt/side: net {adj.sum():.0f}")
for sm in (1,2,3):
    s2 = H.score(df, sigs, risks=(0.005,0.0025), spread_mult=sm, name=f"x{sm}")
    print(H.summary_line(s2))
# bootstrap: share of positive net when resampling trades
rng=np.random.default_rng(0); b=[rng.choice(tr.profit.values,len(tr)).sum() for _ in range(5000)]
print("bootstrap P(net<=0)", np.mean(np.array(b)<=0))
print(tr.sort_values("profit").head(5)[["entry_time","exit_time","side","entry","exit","sl0","lots","profit","r","reason"]].to_string())
