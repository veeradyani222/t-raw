"""Veer's rule (2026-11-01): take whatever was GREAT in the last two years (Oct 2024..Oct 2026), test it
once on one more year (Oct 2023..Oct 2024), then he makes the call.

GREAT = last-2-year profit >= GREAT_PM $/month at 1% of $10K with >= MIN_TRADES trades in those 2 years,
runs live (own symbol, offered). Picked across every strategy on the scoreboard (round-3 pool, live 66,
round-4, round-6 YouTube + written). Sizes for the "great" mix are chosen on the last 2 years too (largest
equal risk keeping the $5K lowest balance >= $4,750 and <= 12 stop days a year on THAT window).
The one test: the year before, replayed exactly on $5K and $10K with the live daily stop.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search6.pick_last2
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from research.search5 import core5 as K
from research.search5.pool5 import build_pool
from research.search5.build_mix import LADDER

GREAT_PM, MIN_TRADES, ADD_RISK = 40.0, 30, 0.005
L2 = K.PERIODS["last2"]; Y1 = K.PERIODS["y1"]; SO = K.PERIODS["sepoct"]
PER = {"y1": Y1, "last2": L2, "sepoct": SO}


def load_all():
    pool = build_pool(); byi = {x["i"]: x for x in pool}
    a = pd.read_csv("research/search5/out/strategy_stats.csv"); a["src2"] = "pool"
    b = pd.read_csv("research/search6/out/spec_stats.csv"); b["src2"] = "r6"; b["offered"] = True; b["runs_live"] = True
    df = pd.concat([a, b], ignore_index=True, sort=False)
    ents = {}; curves = {}
    for r in df.to_dict("records"):
        if r["src2"] == "pool":
            x = byi[int(r["i"])]
            ent = dict(x); z = np.load(K._paths(x["i"])[0])
        else:
            ent = dict(name=r["name"], symbol=r["symbol"], tf=r["tf"], module="research.search6.engine", fn="build_spec",
                       params=dict(spec=json.loads(r["spec"])), group=r["group"], key=f"yt|{r['name']}|{r['symbol']}|{r['tf']}")
            z = np.load(f"research/search6/out/curves/{int(r['i'])}.npz")
        k = f"{r['src2']}:{r['name']}|{r['symbol']}|{r['tf']}"; ents[k] = ent; curves[k] = (z["c"], z["w"])
    df["k"] = [f"{r['src2']}:{r['name']}|{r['symbol']}|{r['tf']}" for r in df.to_dict("records")]
    return df, ents, curves


def window_account(curves, picks, acct, start, end):
    idx, _ = K.seg(next(iter(curves.values()))[0], start, end)
    c = np.zeros(len(idx)); w = np.zeros(len(idx))
    for k, risk in picks:
        f = min(risk * acct["scale"], K.RISK_CAP) / 0.01
        _, sc = K.seg(curves[k][0], start, end); _, sw = K.seg(curves[k][1], start, end)
        c += f * sc; w += f * sw
    fa = K.fast_account(idx, c, w, acct)
    rep = K.period_report(fa["days"], fa["lows"], acct, start, end); rep["years"] = round(K.months_in(start, end) / 12, 1)
    return rep


def main():
    df, ents, curves = load_all()
    ok = df[(df.offered == True) & (df.runs_live == True)].copy()  # noqa: E712
    ok = ok.drop_duplicates("k")
    great = ok[(ok.last2_pm >= GREAT_PM) & (ok.last2_trades >= MIN_TRADES)].sort_values("last2_pm", ascending=False)
    cols = ["name", "symbol", "tf", "src2", "in24", "last2_pm", "last2_trades", "y1_pm", "y1_trades", "sepoct_pm", "dev_pm", "years_dev", "pos_years_dev"]
    pd.set_option("display.width", 230)
    print(f"GREAT in the last 2 years (>= ${GREAT_PM:.0f}/mo at 1%, >= {MIN_TRADES} trades): {len(great)} of {len(ok)}")
    print(great[cols].round(0).to_string(index=False))
    print(f"\nsum at 1% each: last2 ${great.last2_pm.sum():,.0f}/mo (pick window) | TEST year ${great.y1_pm.sum():,.0f}/mo, green {int((great.y1_pm > 0).sum())}/{len(great)} "
          f"| Sep+Oct ${great.sepoct_pm.sum():,.0f}/mo")
    new = great[great.in24 != True]  # noqa: E712
    print(f"of which NOT in the live 24: {len(new)}; their test year ${new.y1_pm.sum():,.0f}/mo, green {int((new.y1_pm > 0).sum())}/{len(new)}")
    great.to_csv("research/search6/out/great_last2.csv", index=False)

    acct5 = K.ACCTS["5k"]
    keys = list(great.k)
    best = None
    for r in LADDER:
        rep = window_account(curves, [(k, r) for k in keys], acct5, *L2)
        print(f"  great @ {r:.2%} each on the PICK window ($5K): ${rep['per_month']}/mo low ${rep['lowest_balance']} stops {rep['stop_days']} fail {rep['failed']}")
        if rep["lowest_balance"] >= 4750 and rep["stop_days"] <= 12 * rep["years"]:
            best = r
    best = best or LADDER[0]
    print(f"  size chosen on the pick window: {best:.2%} each")
    pool = build_pool()
    live23 = [dict(x, risk=x["live_risk"]) for x in pool if "24" in x["mixes"] and x["symbol"] not in K.NOT_OFFERED]
    great_ent = [dict(ents[k], risk=best) for k in keys]
    adds = [dict(ents[k], risk=ADD_RISK) for k in new.k]
    mixes = {"live23": live23, "great (all, sized on last2)": great_ent, "live23 + new greats @0.5%": live23 + adds}
    out = {}
    for name, ent in mixes.items():
        out[name] = {}
        for ak, acct in K.ACCTS.items():
            rep = K.replay_report(ent, acct, K.DEV_END, K.END, PER, label=name); u = rep["periods"]; out[name][ak] = u
            print(f"{name:28} {acct['label']:26} TEST yr ${u['y1']['per_month']}/mo fail {u['y1']['failed']}/{u['y1']['failed'] + u['y1']['passed'] + u['y1']['unfinished']} low ${u['y1']['lowest_balance']} stops {u['y1']['stop_days']} "
                  f"| pick window ${u['last2']['per_month']}/mo fail {u['last2']['failed']} low ${u['last2']['lowest_balance']} | Sep+Oct ${u['sepoct']['per_month']}", flush=True)
    json.dump(dict(rule=dict(great_pm=GREAT_PM, min_trades=MIN_TRADES, size=best), picks=keys, results=out), open("research/search6/out/pick_last2.json", "w"), indent=1, default=str)
    board = dict(mix=[{kk: v for kk, v in m.items() if kk in ("name", "symbol", "tf", "module", "fn", "params", "risk", "group")} for m in great_ent],
                 note=f"Veer's rule 2026-11-01: every strategy with >= ${GREAT_PM:.0f}/mo at 1% over Oct 2024..Oct 2026 and >= {MIN_TRADES} trades, sized {best:.2%} ($10K fraction) on that window. "
                      "The ONE test is Oct 2023..Oct 2024 (research/search6/out/pick_last2.json).")
    json.dump(board, open("docs/board/portfolio-round6-great-last2.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
