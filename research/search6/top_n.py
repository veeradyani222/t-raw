"""Top-N by Veer's rule, sized with the EXACT replay (the fast model undercounts stop days once the daily stop
starts cutting trades). For N in Ns: the N best 'great' strategies by pick-window $/month (Oct 2024..Oct 2026,
testable ones only), equal risk, the largest ladder level whose exact $5K replay on the PICK window keeps the
lowest balance >= LOW and <= STOPS stop days a year. Then the ONE test (Oct 2023..Oct 2024) for that mix,
$5K and $10K.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search6.top_n
"""
import os, sys, json, time
sys.path.insert(0, os.getcwd())
import pandas as pd
from research.search5 import core5 as K
from research.search6.pick_last2 import load_all, PER

Ns = (5, 8, 12, 16)
LADDER = (0.0275, 0.025, 0.02, 0.015, 0.0125, 0.01, 0.0075, 0.005, 0.0025)
LOW, STOPS = 4750, 12


def main():
    df, ents, curves = load_all()
    great = pd.read_csv("research/search6/out/great_last2.csv")
    great = great[great.y1_pm.notna()].sort_values("last2_pm", ascending=False)
    out = {}
    for N in Ns:
        top = great.head(N)
        names = [f"{r.name} {r.symbol} {r.tf}" for r in top.itertuples()]
        print(f"\n=== top {N}: {names}", flush=True)
        chosen = None
        for risk in LADDER:
            ent = [dict(ents[k], risk=risk) for k in top.k]
            t0 = time.time()
            rep = K.replay_report(ent, K.ACCTS["5k"], K.DEV_END, K.END, PER, label=f"top{N}")
            u = rep["periods"]; p = u["last2"]
            ok = p["lowest_balance"] >= LOW and p["stop_days"] <= STOPS * K.months_in(*PER["last2"]) / 12
            print(f"  {risk:.2%} each ($5K): pick window ${p['per_month']}/mo low ${p['lowest_balance']} stops {p['stop_days']} fail {p['failed']} "
                  f"| TEST yr ${u['y1']['per_month']}/mo fail {u['y1']['failed']} low ${u['y1']['lowest_balance']} | Sep+Oct ${u['sepoct']['per_month']} {'OK' if ok else ''} ({time.time() - t0:.0f}s)", flush=True)
            if ok:
                chosen = (risk, u); break
        if chosen is None:
            print("  no size fits the pick-window caps"); out[N] = None; continue
        risk, u5 = chosen
        ent = [dict(ents[k], risk=risk) for k in top.k]
        rep10 = K.replay_report(ent, K.ACCTS["10k"], K.DEV_END, K.END, PER, label=f"top{N}")
        u10 = rep10["periods"]
        print(f"  CHOSEN {risk:.2%}: $10K TEST yr ${u10['y1']['per_month']}/mo fail {u10['y1']['failed']} low ${u10['y1']['lowest_balance']} | pick ${u10['last2']['per_month']}/mo fail {u10['last2']['failed']} | Sep+Oct ${u10['sepoct']['per_month']}", flush=True)
        out[N] = dict(risk=risk, names=names, k5=u5, k10=u10)
        board = dict(mix=[{kk: v for kk, v in m.items() if kk in ("name", "symbol", "tf", "module", "fn", "params", "risk", "group")} for m in ent],
                     note=f"Veer's rule 2026-11-01: top {N} by Oct 2024..Oct 2026 $/month, equal risk {risk:.2%} ($10K fraction, x0.5 on $5K) = largest size whose exact $5K "
                          f"replay on that window keeps lowest >= ${LOW} and <= {STOPS} stop days/yr. ONE test = Oct 2023..Oct 2024 (research/search6/out/top_n.json).")
        json.dump(board, open(f"docs/board/portfolio-round6-top{N}.json", "w"), indent=1, default=str)
    json.dump(out, open("research/search6/out/top_n.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
