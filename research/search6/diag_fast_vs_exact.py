"""Why does the fast sizing model (scaled 1% curves) disagree with the exact replay on stop days?"""
import sys, os
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from research.search5 import core5 as K
from research.search5.pool5 import build_pool
from research.search6.pick_last2 import load_all, L2, PER


def main():
    df, ents, curves = load_all()
    acct = K.ACCTS["5k"]
    pool = build_pool()
    live = [x for x in pool if "24" in x["mixes"] and x["symbol"] not in K.NOT_OFFERED]
    idx, _ = K.seg(curves[next(iter(curves))][0], *L2)
    c = np.zeros(len(idx)); w = np.zeros(len(idx))
    for x in live:
        k = f"pool:{x['name']}|{x['symbol']}|{x['tf']}"; f = min(x["live_risk"] * 0.5, K.RISK_CAP) / 0.01
        c += f * K.seg(curves[k][0], *L2)[1]; w += f * K.seg(curves[k][1], *L2)[1]
    fa = K.fast_account(idx, c, w, acct)
    print("live23 FAST pick window: net/mo", round(fa["net"] / K.months_in(*L2)), "low", round(fa["low"] + 5000), "halts", fa["halts"], "(exact was $696/mo, low 4807, 21 stops)")
    k = "pool:bos_trail3_htfD50_H1|XAUUSD|H1"; x = dict(ents[k], risk=0.0275)
    f = min(0.0275 * 0.5, K.RISK_CAP) / 0.01
    c1 = f * K.seg(curves[k][0], *L2)[1]; w1 = f * K.seg(curves[k][1], *L2)[1]
    fa1 = K.fast_account(idx, c1, w1, acct); print("bos H1 @2.75% FAST: net/mo", round(fa1["net"] / 24.4), "low", round(fa1["low"] + 5000), "halts", fa1["halts"])
    rep = K.replay_report([x], acct, K.DEV_END, K.END, PER, label="one"); print("bos H1 @2.75% EXACT:", rep["periods"]["last2"])
    runs = K.mix_sims([x], acct, K.DEV_END, K.END); _, cv, t = runs[0]
    t = t[(t.entry_time >= L2[0]) & (t.entry_time < L2[1])]
    print("exact trades", len(t), "max |profit|", round(t.profit.abs().max()), "target risk/trade", 0.0275 * 0.5 * 10000, "max lots", t.lots.max())
    t2 = pd.read_pickle(K._paths(ents[k]["i"])[1]); t2 = t2[(t2.entry_time >= L2[0]) & (t2.entry_time < L2[1])]
    print("cached 1% trades", len(t2), "max |profit| at 1%", round(t2.profit.abs().max()), "x1.375 =", round(t2.profit.abs().max() * 1.375), "max lots", t2.lots.max())
    # day-low distribution: exact vs fast for this one strategy
    d_ex = rep["day_low"][(rep["day_low"].index >= L2[0]) & (rep["day_low"].index < L2[1])]
    print("exact days <= -125:", int((d_ex <= -125).sum()), " fast days <= -125:", int((fa1["lows"] <= -125).sum()))
    print("exact 10 worst days:", d_ex.nsmallest(10).round(0).to_dict())
    print("fast  10 worst days:", fa1["lows"].nsmallest(10).round(0).to_dict())


if __name__ == "__main__":
    main()
