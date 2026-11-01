"""The live 23 on bigger FundedNext accounts ($25K, $50K), exact replay, same periods."""
import os, sys, json
sys.path.insert(0, os.getcwd())
from research.search5 import core5 as K
from research.search5.pool5 import build_pool
from research.search6.pick_last2 import PER


def main():
    pool = build_pool()
    DROP = {"rsi2_mr_jpn225_h1", "brent_wti_spread_z"}   # 1-lot minimum: unfunded small, a disaster big; cross-symbol: cannot run live
    live23 = [dict(x, risk=x["live_risk"]) for x in pool if "24" in x["mixes"] and x["symbol"] not in K.NOT_OFFERED and x["name"] not in DROP]
    print(f"{len(live23)} strategies (dropped {sorted(DROP)})")
    out = {}
    for ak, acct in {**{"5k": K.ACCTS["5k"], "10k": K.ACCTS["10k"]}, **K.BIG_ACCTS}.items():
        rep = K.replay_report(live23, acct, K.DEV_END, K.END, PER, label="live23"); u = rep["periods"]; out[ak] = u
        print(f"{acct['label']:28} TEST yr ${u['y1']['per_month']:>6}/mo fail {u['y1']['failed']:2}/24 low ${u['y1']['lowest_balance']:>7,} stops {u['y1']['stop_days']:3} "
              f"| last 2y ${u['last2']['per_month']:>6}/mo fail {u['last2']['failed']:2} low ${u['last2']['lowest_balance']:>7,} stops {u['last2']['stop_days']:3} | Sep+Oct ${u['sepoct']['per_month']:>6}/mo", flush=True)
    json.dump(out, open("research/search6/out/live23_big.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
