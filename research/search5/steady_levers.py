"""Can the steady 33 make more? Two honest levers on the $5K account: risk per strategy and the bot's
daily close-all level (MULTI_DAILY_STOP_FRAC: today -$125 of the firm's -$200). Grid chosen on dev
(2015..2023-10-20, fast model: lowest balance >= $4,750, <= 12 stop days a year), every cell then
replayed exactly on the unseen periods.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search5.steady_levers
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from research.search5 import core5 as K
from research.search5.pool5 import build_pool
from research.search5.build_mix import dev_account, UNSEEN

RISKS = (0.003, 0.004, 0.005, 0.006)
HALTS = (125.0, 150.0, 175.0)          # close-all level; slip 10% of it; the firm's hard limit is -$200


def acct_for(halt):
    a = dict(K.ACCTS["5k"]); a["halt"] = halt; a["slip"] = round(halt * 0.1, 1); a["label"] = f"$5K stop -${halt:.0f}"
    return a


def main():
    pool = build_pool(); C, W, _ = K.load_full(pool)
    board = json.load(open("docs/board/portfolio-round5-honest.json"))["mix"]
    byname = {(x["name"], x["symbol"], x["tf"]): x for x in pool}
    base = [byname[(m["name"], m["symbol"], m["tf"])] for m in board]
    rows = []
    for halt in HALTS:
        acct = acct_for(halt)
        for r in RISKS:
            ent = [dict(x, risk=r) for x in base]
            d = dev_account(pool, C, W, ent, acct)
            ok = d["lowest_balance"] >= 4750 and d["stop_days"] <= 12 * d["years"]
            print(f"stop -${halt:.0f} risk {r:.2%}: dev ${d['per_month']}/mo low ${d['lowest_balance']} stops {d['stop_days']} fail {d['failed']} {'OK' if ok else 'x'}", flush=True)
            rows.append(dict(halt=halt, risk=r, dev=d, dev_ok=ok, ent=ent, acct=acct))
    out = []
    for row in rows:
        rep = K.replay_report(row["ent"], row["acct"], K.DEV_END, K.END, UNSEEN, label=f"{row['halt']}/{row['risk']}")
        u = rep["periods"]
        print(f"stop -${row['halt']:.0f} risk {row['risk']:.2%} {'DEV-OK' if row['dev_ok'] else 'dev-x '}: unseen yr ${u['y1']['per_month']}/mo fail {u['y1']['failed']} low ${u['y1']['lowest_balance']} "
              f"| last2 ${u['last2']['per_month']}/mo fail {u['last2']['failed']} | Sep+Oct ${u['sepoct']['per_month']} | 3y ${u['unseen3']['per_month']}/mo fail {u['unseen3']['failed']} stops {u['unseen3']['stop_days']} worst day ${u['unseen3']['worst_day']}", flush=True)
        out.append(dict(halt=row["halt"], risk=row["risk"], dev=row["dev"], dev_ok=row["dev_ok"], unseen=u))
    json.dump(out, open(os.path.join(K.OUT, "steady_levers.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
