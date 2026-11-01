"""Round-5 mix building, honest version: every pick and every size is decided on dev data
(2015-01-01..2023-10-20); the three unseen periods are then replayed EXACTLY (sims at the
account's risk, the live close-all daily stop) for the $5K and the $10K account.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search5.build_mix

Selection rules (fixed before looking at unseen data for the pool; see screen.md):
    strict   >= 5 dev years, >= 80% green dev years, dev $/month > 0
    relaxed  >= 4 dev years, >= 50% green dev years, dev $/month > 0, >= 60 dev trades
Only strategies that can run live (own symbol only, offered by FundedNext) qualify.

Mixes:
    live23      the live 24 minus SOLUSD, at the live risks
    live23+adds live23 + relaxed-rule strategies not in the 24, each at ADD_RISK ($10K fraction)
    honest      relaxed-rule strategies only (24 members included when they pass), equal risk
                picked on dev: largest ladder level with dev lowest balance >= -$250 ($5K) and
                <= 12 stop days a year
    pruned+adds live23 minus its dev losers (dev $/month < -$20 at 1%) + the adds

Regime switch (idea 4): on the replayed daily P&L, size x0.5 on days when the mix's own
20-day mean equity sits below its 60-day mean (known at the previous close). Approximate:
scales the day's P&L and low; the daily stop is not re-simulated.
Writes out/mixes.json, out/mixes.md and docs/board/portfolio-round5-<name>.json for every mix.
"""
import os, sys, json
sys.path.insert(0, os.getcwd())
import numpy as np, pandas as pd
from research.search5 import core5 as K
from research.search5.pool5 import build_pool

ADD_RISK = 0.005
LADDER = (0.0025, 0.003, 0.0035, 0.004, 0.0045, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02)
DEV_LOW_5K, DEV_STOPS_PER_YEAR = -250.0, 12
UNSEEN = {"y1": K.PERIODS["y1"], "last2": K.PERIODS["last2"], "sepoct": K.PERIODS["sepoct"], "unseen3": K.PERIODS["unseen3"]}


def rules(st):
    ok = st.get("offered", False) and st.get("runs_live", False) and (st.get("years_dev") or 0) > 0
    strict = ok and st["years_dev"] >= 5 and st["steady_dev"] >= 0.8 and st["dev_pm"] > 0
    relaxed = ok and st["years_dev"] >= 4 and st["steady_dev"] >= 0.5 and st["dev_pm"] > 0 and st["dev_trades"] >= 60
    return strict, relaxed


def dev_account(pool, C, W, entries, acct):
    """Fast dev-period account numbers from the cached 1% curves, scaled by each entry's risk."""
    idx, _ = K.seg(C[0], K.START, K.DEV_END)
    c = np.zeros(len(idx)); w = np.zeros(len(idx))
    for m in entries:
        f = min(m["risk"] * acct["scale"], K.RISK_CAP) / 0.01
        _, sc = K.seg(C[m["i"]], K.START, K.DEV_END); _, sw = K.seg(W[m["i"]], K.START, K.DEV_END)
        c += f * sc; w += f * sw
    fa = K.fast_account(idx, c, w, acct)
    rep = K.period_report(fa["days"], fa["lows"], acct, K.START, K.DEV_END)
    rep["years"] = round(K.months_in(K.START, K.DEV_END) / 12, 1)
    return rep


def regime_switch(dp, dl, short=20, long=60):
    eq = dp.cumsum()
    sig = (eq.rolling(short).mean() < eq.rolling(long).mean()).shift(1).fillna(False)
    f = np.where(sig, 0.5, 1.0)
    return dp * f, dl * f, float(sig.mean())


def main():
    pool = build_pool()
    C, W, trades = K.load_full(pool)
    stats = {}
    for x in pool:
        if trades[x["i"]] is None:
            continue
        s = K.strat_stats(x, C[x["i"]], W[x["i"]], trades[x["i"]]); s["runs_live"] = x["runs_live"]
        s["strict"], s["relaxed"] = rules(s); stats[x["i"]] = s
    byi = {x["i"]: x for x in pool}
    live23 = [dict(byi[i], risk=byi[i]["live_risk"]) for i in stats if stats[i]["in24"] and byi[i]["symbol"] not in K.NOT_OFFERED]
    relaxed = [i for i in stats if stats[i]["relaxed"]]
    strict = [i for i in stats if stats[i]["strict"]]
    adds = [dict(byi[i], risk=ADD_RISK) for i in relaxed if not stats[i]["in24"]]
    losers = [i for i in stats if stats[i]["in24"] and (stats[i].get("dev_pm") is not None) and stats[i]["dev_pm"] < -20]
    print(f"live23: {len(live23)} | relaxed rule: {len(relaxed)} ({len(adds)} not in the 24) | strict rule: {len(strict)} | dev losers in the 24: {len(losers)}")
    for i in relaxed:
        s = stats[i]; print(f"  relaxed: {s['name']:36} {s['symbol']:7} {s['tf']:3} dev ${s['dev_pm']:5.0f}/mo {s['pos_years_dev']}/{s['years_dev']} green{'  [in 24]' if s['in24'] else ''}{'  [STRICT]' if s['strict'] else ''}")
    print("  dev losers in the 24:", [f"{stats[i]['name']} {stats[i]['symbol']} ({stats[i]['dev_pm']:.0f}/mo)" for i in losers])

    # equal-risk mixes sized on dev at $5K: largest ladder level that keeps the dev caps
    acct5 = K.ACCTS["5k"]

    def size_on_dev(ids, label):
        best = None
        for r in LADDER:
            ent = [dict(byi[i], risk=r) for i in ids]
            rep = dev_account(pool, C, W, ent, acct5)
            print(f"  {label} @ {r:.2%} each (dev, $5K): ${rep['per_month']}/mo, lowest ${rep['lowest_balance']}, stop days {rep['stop_days']} ({rep['stop_days'] / rep['years']:.1f}/yr), failed {rep['failed']}/{rep['failed'] + rep['passed'] + rep['unfinished']}")
            if rep["lowest_balance"] - acct5["start_bal"] >= DEV_LOW_5K and rep["stop_days"] <= DEV_STOPS_PER_YEAR * rep["years"]:
                best = (r, ent)
        if best is None:
            best = (LADDER[0], [dict(byi[i], risk=LADDER[0]) for i in ids])
        print(f"  {label} mix: {len(best[1])} strategies at {best[0]:.2%} each ($10K fraction)")
        return best
    honest = size_on_dev(relaxed, "honest")
    strict_mix = size_on_dev(strict, "strict")

    mixes = {
        "live23": live23,
        "live23+adds": live23 + adds,
        "honest": honest[1],
        "strict": strict_mix[1],
        "pruned+adds": [m for m in live23 if m["i"] not in losers] + adds,
    }
    results = {}
    for name, ent in mixes.items():
        results[name] = dict(n=len(ent), strategies=[dict(name=m["name"], symbol=m["symbol"], tf=m["tf"], risk=m["risk"]) for m in ent], accounts={})
        for ak, acct in K.ACCTS.items():
            dev = dev_account(pool, C, W, ent, acct)
            rep = K.replay_report(ent, acct, K.DEV_END, K.END, UNSEEN, label=name)
            dp2, dl2, share = regime_switch(rep["day_pnl"], rep["day_low"])
            sw = {lab: K.period_report(dp2, dl2, acct, a, b) for lab, (a, b) in UNSEEN.items()}
            results[name]["accounts"][ak] = dict(dev_fast=dev, unseen=rep["periods"], regime_switch=sw, switch_share=share,
                                                   per_strategy=rep["per_strategy"], halts=rep["info"]["halts"])
            u = rep["periods"]
            print(f"{name:12} {acct['label']:26} dev(fast) ${dev['per_month']}/mo low ${dev['lowest_balance']} | unseen yr ${u['y1']['per_month']}/mo fail {u['y1']['failed']} low ${u['y1']['lowest_balance']} "
                  f"| last2 ${u['last2']['per_month']}/mo fail {u['last2']['failed']} low ${u['last2']['lowest_balance']} | Sep+Oct ${u['sepoct']['per_month']}/mo "
                  f"| switch: y1 ${sw['y1']['per_month']} last2 ${sw['last2']['per_month']} (half-size {share:.0%} of days)", flush=True)
    json.dump(dict(mixes=results, rules=dict(strict=[stats[i]["name"] + " " + stats[i]["symbol"] for i in strict], relaxed=[stats[i]["name"] + " " + stats[i]["symbol"] for i in relaxed],
                                            losers=[stats[i]["name"] + " " + stats[i]["symbol"] for i in losers], honest_risk=honest[0], strict_risk=strict_mix[0], add_risk=ADD_RISK)),
              open(os.path.join(K.OUT, "mixes.json"), "w"), indent=1, default=str)
    # board files (never the live file)
    for name, ent in mixes.items():
        if name == "live23":
            continue
        board = dict(mix=[dict(name=m["name"], symbol=m["symbol"], tf=m["tf"], family=m.get("family"), module=m["module"], fn=m["fn"], params=m["params"],
                               risk=m["risk"], src=m["src"], group=m["group"], in_live24=("24" in m["mixes"])) for m in ent],
                     results={ak: dict(dev_fast=v["dev_fast"], unseen=v["unseen"], regime_switch=v["regime_switch"]) for ak, v in results[name]["accounts"].items()},
                     note=f"Round 5 (2026-11-01) '{name}': picks and sizes decided on 2015..2023-10-20 only (research/search5/build_mix.py); "
                          "risk = $10K fraction (x0.5 on the $5K account, capped 2.75%). Unseen periods replayed exactly with the live close-all stop. "
                          "last2 (Oct 2024..Oct 2026) is the window the round-3 pool and the 66 were searched on: a fit period for those strategies.")
        json.dump(board, open(f"docs/board/portfolio-round5-{name.replace('+', '-')}.json", "w"), indent=1, default=str)
    print("DONE")


if __name__ == "__main__":
    main()
