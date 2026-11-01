"""Why is the $25K replay not 2.5x the $10K one? Per-strategy trade counts and profit per unit of scale."""
import os, sys
sys.path.insert(0, os.getcwd())
import pandas as pd
from research.search5 import core5 as K
from research.search5.pool5 import build_pool


def main():
    pool = build_pool()
    live = [dict(x, risk=x["live_risk"]) for x in pool if "24" in x["mixes"] and x["symbol"] not in K.NOT_OFFERED]
    rows = {}
    for ak, acct in (("10k", K.ACCTS["10k"]), ("25k", K.BIG_ACCTS["25k"])):
        for (k, cv, t), m in zip(K.mix_sims(live, acct, K.DEV_END, K.END), live):
            rows.setdefault(m["name"] + " " + m["symbol"], {})[ak] = (len(t), float(t.profit.sum()) / acct["scale"] if len(t) else 0.0,
                                                                    float(t.lots.max()) if len(t) else 0.0, float(t.profit.min()) / acct["scale"] if len(t) else 0.0)
    print(f"{'strategy':40} {'trades 10k/25k':>16} {'profit/scale 10k':>16} {'25k':>8} {'maxlots 10k/25k':>16} {'worst trade/scale 10k':>22} {'25k':>8}")
    for n, r in rows.items():
        a, b = r["10k"], r["25k"]
        print(f"{n:40} {a[0]:7d}/{b[0]:<8d} {a[1]:16,.0f} {b[1]:8,.0f} {a[2]:7.2f}/{b[2]:<8.2f} {a[3]:22,.0f} {b[3]:8,.0f}")


if __name__ == "__main__":
    main()
