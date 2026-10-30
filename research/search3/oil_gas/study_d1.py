"""D1 market study on WTI/Brent (Dukascopy daily files as a stand-in until IC Markets files land)."""
import pandas as pd, numpy as np
for sym in ("xtiusd","xbrusd","xngusd"):
    d=pd.read_csv(f"data/search/{sym}-d1.csv",parse_dates=["time"]).sort_values("time")
    d=d[d.time>="2019-01-01"].reset_index(drop=True)
    d["ret"]=np.log(d.close/d.close.shift())
    d["rng"]=(d.high-d.low)/d.close
    d["wd"]=d.time.dt.weekday
    print("\n==",sym,len(d),d.time.min().date(),d.time.max().date())
    print("weekday mean ret bp / range %:"); print((d.groupby("wd").ret.mean()*1e4).round(1).to_dict(), (d.groupby("wd").rng.mean()*100).round(2).to_dict())
    # autocorrelation of daily returns by lag
    print("acf lags1-5:",[round(d.ret.autocorr(k),3) for k in range(1,6)])
    # trend persistence: sign of N-day return vs next-day ret
    for n in (5,10,20,60):
        m=np.sign(d.close.diff(n)); nxt=d.ret.shift(-1)
        print(f" mom{n}: next ret when up {nxt[m>0].mean()*1e4:.1f}bp  when down {nxt[m<0].mean()*1e4:.1f}bp")
    # gap: open vs prev close, fill rate
    d["gap"]=d.open-d.close.shift(); d["gapp"]=d.gap/d.close.shift()
    big=d[d.gapp.abs()>0.005]
    fill=((big.gap>0)&(big.low<=big.close.shift()))|((big.gap<0)&(big.high>=big.close.shift()))
    print(f" gaps>0.5%: {len(big)} fill-same-day {fill.mean():.2f}; gap-day ret sign agree {np.mean(np.sign(big.gapp)==np.sign(big.close-big.open)):.2f}")
    # volatility by weekday (wed EIA)
    print(" range by wd:",(d.groupby("wd").rng.median()*100).round(2).to_dict())
    # close-to-open vs open-to-close
    d["oc"]=np.log(d.close/d.open); d["co"]=np.log(d.open/d.close.shift())
    print(f" mean open->close {d.oc.mean()*1e4:.1f}bp  close->open {d.co.mean()*1e4:.1f}bp")
    # 2024-10-20+
    e=d[d.time>="2024-10-20"]
    print(" recent weekday ret bp:",(e.groupby("wd").ret.mean()*1e4).round(1).to_dict(), "acf1",round(e.ret.autocorr(1),3))
# brent-wti spread
a=pd.read_csv("data/search/xtiusd-d1.csv",parse_dates=["time"]); b=pd.read_csv("data/search/xbrusd-d1.csv",parse_dates=["time"])
m=a.merge(b,on="time",suffixes=("_w","_b")); m=m[m.time>="2019-01-01"]
sp=m.close_b-m.close_w
print("\nBrent-WTI spread: mean",sp.mean().round(2),"std",sp.std().round(2),"acf1",round(sp.autocorr(1),3),"acf5",round(sp.autocorr(5),3))
z=(sp-sp.rolling(20).mean())/sp.rolling(20).std()
nxt=sp.shift(-1)-sp
print(" z>1.5 next-day spread change",nxt[z>1.5].mean().round(3),"n",(z>1.5).sum()," z<-1.5",nxt[z<-1.5].mean().round(3),"n",(z<-1.5).sum())
