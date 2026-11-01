"""Fewer and bigger: a greedy $5K mix from the 65 'great' strategies, built on the PICK window
(Oct 2024..Oct 2026, Veer's rule), then tested once on Oct 2023..Oct 2024.

Greedy: repeatedly raise one strategy one risk level (ladder 0.25%..2.75% of $10K, i.e. $12.5..$137 per
trade on $5K) where it adds the most pick-window profit, as long as the $5K account on the pick window keeps
lowest balance >= LOW and <= STOPS_PER_YEAR stop days a year. Two settings (tight / loose). Then exact
replay of the result on both accounts, test year first.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search6.top_greats
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from research.search5 import core5 as K
from research.search6.pick_last2 import load_all, PER, L2, Y1

LEVELS = (0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.025, 0.0275)
SETTINGS = {"tight": dict(low=4750, stops=12), "loose": dict(low=4700, stops=24)}


def greedy(curves, keys, acct, start, end, low, stops_per_year):
    idx, _ = K.seg(curves[keys[0]][0], start, end)
    segs = {k: (K.seg(curves[k][0], start, end)[1].astype(float), K.seg(curves[k][1], start, end)[1].astype(float)) for k in keys}
    years = K.months_in(start, end) / 12
    lvl = {k: -1 for k in keys}
    c = np.zeros(len(idx)); w = np.zeros(len(idx))

    def ok(c_, w_):
        fa = K.fast_account(idx, c_, w_, acct)
        return fa["low"] + acct["start_bal"] >= low and fa["halts"] <= stops_per_year * years, fa

    while True:
        best = None
        for k in keys:
            if lvl[k] + 1 >= len(LEVELS):
                continue
            f_new = min(LEVELS[lvl[k] + 1] * acct["scale"], K.RISK_CAP) / 0.01
            f_old = (min(LEVELS[lvl[k]] * acct["scale"], K.RISK_CAP) / 0.01) if lvl[k] >= 0 else 0.0
            dc = (f_new - f_old) * segs[k][0]; dw = (f_new - f_old) * segs[k][1]
            gain = dc[-1]
            if gain <= 0 or (best is not None and gain <= best[0]):
                continue
            good, fa = ok(c + dc, w + dw)
            if good:
                best = (gain, k, dc, dw, fa)
        if best is None:
            break
        _, k, dc, dw, fa = best; lvl[k] += 1; c += dc; w += dw
    chosen = {k: LEVELS[l] for k, l in lvl.items() if l >= 0}
    fa = K.fast_account(idx, c, w, acct)
    return chosen, fa


def main():
    df, ents, curves = load_all()
    great = pd.read_csv("research/search6/out/great_last2.csv")
    keys = [k for k in great.k if k in curves]
    acct5 = K.ACCTS["5k"]
    results = {}
    for tag, st in SETTINGS.items():
        chosen, fa = greedy(curves, keys, acct5, *L2, st["low"], st["stops"])
        print(f"\n=== {tag}: lowest >= ${st['low']}, <= {st['stops']} stop days/yr on the pick window -> {len(chosen)} strategies, "
              f"pick window (fast model) ${fa['net'] / K.months_in(*L2):,.0f}/mo, low ${fa['low'] + 5000:,.0f}, stop days {fa['halts']}")
        rows = great.set_index("k").loc[list(chosen)]
        for k, r in zip(chosen, rows.itertuples()):
            print(f"  {chosen[k]:.2%}  {r.name:42} {r.symbol:7} {r.tf:3}  pick ${r.last2_pm:5.0f}/mo  TEST ${r.y1_pm if pd.notna(r.y1_pm) else float('nan'):6.0f}/mo  Sep+Oct ${r.sepoct_pm:5.0f}")
        ent = [dict(ents[k], risk=chosen[k]) for k in chosen]
        results[tag] = dict(risks={k: chosen[k] for k in chosen}, accounts={})
        for ak, acct in K.ACCTS.items():
            rep = K.replay_report(ent, acct, K.DEV_END, K.END, PER, label=tag); u = rep["periods"]; results[tag]["accounts"][ak] = u
            print(f"  EXACT {acct['label']:26} TEST yr ${u['y1']['per_month']}/mo fail {u['y1']['failed']}/{u['y1']['failed'] + u['y1']['passed'] + u['y1']['unfinished']} low ${u['y1']['lowest_balance']} stops {u['y1']['stop_days']} "
                  f"| pick window ${u['last2']['per_month']}/mo fail {u['last2']['failed']} low ${u['last2']['lowest_balance']} stops {u['last2']['stop_days']} | Sep+Oct ${u['sepoct']['per_month']}", flush=True)
        board = dict(mix=[{kk: v for kk, v in m.items() if kk in ("name", "symbol", "tf", "module", "fn", "params", "risk", "group")} for m in ent],
                     note=f"Veer's rule 2026-11-01, '{tag}': greedy on Oct 2024..Oct 2026 from the 65 great strategies, $5K lowest >= ${st['low']}, "
                          f"<= {st['stops']} stop days/yr on that window. Risk = $10K fraction (x0.5 on $5K). ONE test = Oct 2023..Oct 2024, in research/search6/out/top_greats.json.")
        json.dump(board, open(f"docs/board/portfolio-round6-top-{tag}.json", "w"), indent=1, default=str)
    json.dump(results, open("research/search6/out/top_greats.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
