"""The earlier mixes (66, 74, 51) vs the live 23, exact $5K and $10K replay, same periods (SOLUSD and
cross-symbol strategies dropped, as live would)."""
import os, sys, json
sys.path.insert(0, os.getcwd())
from research.search2.portfolio import core as P
from research.search5 import core5 as K
from research.search5.pool5 import build_pool, CROSS_SYMBOL
from research.search6.pick_last2 import PER

FILES = {"live 23": "docs/board/portfolio-round3-24.json", "the 66": "docs/board/portfolio-lp300-66.json",
         "the 74": "docs/board/portfolio-round3.json", "the 51": "docs/board/portfolio-round3-2y.json"}


def main():
    pool = {x["key"]: x for x in build_pool()}
    out = {}
    for lab, path in FILES.items():
        ent = []
        for m in json.load(open(path))["mix"]:
            x = pool.get(P.keyof(m))
            if x is None or m["symbol"] in K.NOT_OFFERED or m["fn"] in CROSS_SYMBOL:
                continue
            ent.append(dict(x, risk=m["risk"]))
        out[lab] = {"n": len(ent)}
        for ak in ("5k", "10k"):
            acct = K.ACCTS[ak]
            rep = K.replay_report(ent, acct, K.DEV_END, K.END, PER, label=lab); u = rep["periods"]; out[lab][ak] = u
            print(f"{lab:8} ({len(ent):2} run live) {acct['label']:26} TEST yr ${u['y1']['per_month']:>5}/mo fail {u['y1']['failed']:2}/24 low ${u['y1']['lowest_balance']:>6,} stops {u['y1']['stop_days']:3} "
                  f"| last 2y ${u['last2']['per_month']:>6}/mo fail {u['last2']['failed']:2} low ${u['last2']['lowest_balance']:>6,} stops {u['last2']['stop_days']:3} | Sep+Oct ${u['sepoct']['per_month']:>6}/mo", flush=True)
    json.dump(out, open("research/search6/out/mixes_compare.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
