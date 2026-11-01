"""Does adding the round-6 dev-rule passers to the live 23 help? Exact $5K / $10K replay of
live23, live23 + round-6 passers (each at ADD_RISK, a $10K fraction), and the passers alone, on the
three unseen periods, with the live close-all daily stop. Picks are the dev-rule passers only
(no unseen data used to choose).

    cd mt5-trader && .venv/Scripts/python.exe -m research.search6.add_to_live
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import pandas as pd
from research.search5 import core5 as K
from research.search5.pool5 import build_pool
from research.search5.build_mix import UNSEEN, rules

ADD_RISK = 0.005


def main():
    st = pd.read_csv("research/search6/out/spec_stats.csv")
    st["offered"] = True; st["runs_live"] = True
    ok = st[[rules(r)[1] for r in st.to_dict("records")]]
    adds = [dict(name=r["name"], symbol=r["symbol"], tf=r["tf"], module="research.search6.engine", fn="build_spec",
                 params=dict(spec=json.loads(r["spec"])), group=r["group"], risk=ADD_RISK, key=f"yt|{r['name']}|{r['symbol']}|{r['tf']}")
            for r in ok.to_dict("records")]
    pool = build_pool()
    live23 = [dict(x, risk=x["live_risk"]) for x in pool if "24" in x["mixes"] and x["symbol"] not in K.NOT_OFFERED]
    print(f"live 23 + {len(adds)} round-6 passers at {ADD_RISK:.2%} each:", [a["name"] for a in adds])
    out = {}
    for name, ent in (("live23", live23), ("live23+r6", live23 + adds), ("r6 alone", adds)):
        out[name] = {}
        for ak, acct in K.ACCTS.items():
            rep = K.replay_report(ent, acct, K.DEV_END, K.END, UNSEEN, label=name)
            u = rep["periods"]; out[name][ak] = u
            print(f"{name:10} {acct['label']:26} unseen yr ${u['y1']['per_month']}/mo fail {u['y1']['failed']}/{u['y1']['failed'] + u['y1']['passed'] + u['y1']['unfinished']} low ${u['y1']['lowest_balance']} "
                  f"| last2 ${u['last2']['per_month']}/mo fail {u['last2']['failed']} | Sep+Oct ${u['sepoct']['per_month']} | 3y ${u['unseen3']['per_month']}/mo fail {u['unseen3']['failed']} stops {u['unseen3']['stop_days']}", flush=True)
    json.dump(out, open("research/search6/out/add_to_live.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
