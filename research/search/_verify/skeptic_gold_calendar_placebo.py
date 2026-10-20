import os, sys
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
os.environ["PROP_OOS"] = "1"
import pandas as pd, numpy as np
from research.prop import harness as H
import research.search.published_research.strategies as S
P = {"tom_days_before": 0, "tom_hold": 4, "fomc_sl": 1.5}

def placebo(df, rng):
    # same structure: per month one 1-day long (1.5 dATR stop, entry h20, exit h20 next day)
    # and one 4-day long (2 dATR stop, entry h22) on RANDOM business days of the month
    n=len(df); out=[None]*n
    t=pd.DatetimeIndex(df.time); hr=t.hour.to_numpy(); days=t.normalize()
    datr=S._daily_atr_on_bars(df); c=df.close.to_numpy(float)
    per_day=max(1,int(round(pd.Series(days).value_counts().median())))
    ud=pd.DatetimeIndex(days.unique()); m=ud.to_period("M")
    pick1=set(); pick2=set()
    for per in m.unique():
        dd=ud[m==per]
        if len(dd)<3: continue
        a,b=rng.choice(len(dd),2,replace=False); pick1.add(dd[a]); pick2.add(dd[b])
    for i in range(n):
        if not np.isfinite(datr[i]): continue
        if hr[i]==20 and days[i] in pick1:
            out[i]=H.Entry("long", c[i]-1.5*datr[i], exit_hour=20, max_hold=40)
        elif hr[i]==22 and days[i] in pick2 and out[i] is None:
            out[i]=H.Entry("long", c[i]-2.0*datr[i], max_hold=4*per_day)
    return out

def am(df, sigs, risk=0.02, start=None):
    r=H.simulate(df, sigs, risk=risk); t=r["trades"]
    if start: t=t[t.entry_time>=start]
    months=len(pd.period_range(start or df.time.iloc[0], df.time.iloc[-1], freq="M"))
    return t.profit.sum()/months, len(t), t

for split,start in (("oos","2024-01-01"),("is",None)):
    df=H.load("XAUUSD","H1",split=split)
    real,nt,tr=am(df, S.build_gold_calendar(df,**P), start=start)
    vals=[]
    for s in range(40):
        v,_,_=am(df, placebo(df,np.random.default_rng(s)), start=start); vals.append(v)
    vals=np.array(vals)
    print(split, "real $/mo", round(real,1), "trades", nt, "| placebo mean", round(vals.mean(),1),
          "median", round(np.median(vals),1), "p90", round(np.quantile(vals,.9),1),
          "pct placebo >= real", (vals>=real).mean())
    # swap estimate: long gold financing ~ (USD rate + 2.5% markup)/360 * notional per night, triple Wed
    rate = 0.05 if split=="oos" else 0.015
    sw=0.0
    for _,r in tr.iterrows():
        nights=pd.date_range(r.entry_time.normalize(), r.exit_time.normalize()-pd.Timedelta(days=1), freq="D")
        k=sum(3 if d.weekday()==2 else (0 if d.weekday()>=5 else 1) for d in nights)
        sw += k * r.entry*100*r.lots*(rate+0.025)/360
    months=len(pd.period_range(start or df.time.iloc[0], df.time.iloc[-1], freq="M"))
    print(split, "est swap total", round(sw,1), "per month", round(sw/months,1))
