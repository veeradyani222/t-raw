import os, sys
sys.path.insert(0, r"C:/Users/veera/Desktop/mt5-trader")
os.environ["PROP_OOS"] = "1"
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search.gold_fix.strategies import build_gold_lowvol_donchian as build
P = dict(n_entry=15, n_exit=7, atr_stop=2, trail_atr=5, atrp_max=0.5, atrp_window=500, adx_min=20)
SWAP_LONG, SWAP_SHORT = -60.0, 30.0  # $/lot/night rough assumption for gold at retail prop brokers (long strongly negative)
for split in ("is", "oos"):
    df = H.load("XAUUSD", "H4", split=split)
    sigs = build(df, **P)
    nsig = sum(e is not None for e in sigs)
    for risk in (0.005, 0.0075):
        r = H.simulate(df, sigs, risk=risk)
        t = r["trades"] if isinstance(r["trades"], pd.DataFrame) else pd.DataFrame(r["trades"])
        if split == "oos":
            t = t[t.entry_time >= pd.Timestamp("2024-01-01")]
        if t.empty:
            print(split, risk, "no trades"); continue
        t = t.copy()
        t["days"] = (t.exit_time - t.entry_time).dt.total_seconds() / 86400
        t["nights"] = np.floor(t["days"]).clip(lower=0)
        t["swap"] = np.where(t.side == "long", SWAP_LONG, SWAP_SHORT) * t.lots * t.nights
        p = t.profit.sort_values(ascending=False)
        print(f"\n== {split} risk {risk}: signals {nsig} trades {len(t)} net {t.profit.sum():.0f} "
              f"top1 {p.iloc[0]:.0f} top2 {p.iloc[:2].sum():.0f} top5 {p.iloc[:5].sum():.0f} "
              f"net_ex_top2 {t.profit.sum()-p.iloc[:2].sum():.0f}")
        print(f"   median hold days {t.days.median():.1f} mean {t.days.mean():.1f}; long n {sum(t.side=='long')} "
              f"long net {t[t.side=='long'].profit.sum():.0f} short net {t[t.side=='short'].profit.sum():.0f}")
        print(f"   est swap ({SWAP_LONG}/lot/night long): {t.swap.sum():.0f} -> net after swap {t.profit.sum()+t.swap.sum():.0f}")
        print(f"   mean lots {t.lots.mean():.3f}, min lots {t.lots.min():.2f}, reasons {t.reason.value_counts().to_dict()}")
        t["yr"] = t.entry_time.dt.year
        print("   by year:", t.groupby("yr").profit.sum().round(0).to_dict())
        if split == "oos":
            print(t[["entry_time","exit_time","side","lots","profit","reason"]].to_string())
    # min-lot skips: signals with atr*2 loss per 0.01 lot > 50
    if split == "oos":
        idx = [i for i,e in enumerate(sigs) if e is not None and df.time.iat[i] >= pd.Timestamp("2024-01-01")]
        lossper001 = [ (abs(df.close.iat[i]-sigs[i].sl)+0.3)*100*0.01 + 0.14 for i in idx]
        print("OOS signals", len(idx), "skipped at 0.5% (0.01 lot loss > $50):", sum(x>50 for x in lossper001),
              "at 0.75%:", sum(x>75 for x in lossper001))
    # buy and hold beta
    c = df.close.to_numpy()
    print(split, "gold B&H move", c[0], "->", c[-1])
