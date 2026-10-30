"""Round-3 portfolio build from the FULL pool (80 new candidates + the live 66), no
preference for the current mix.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search3.portfolio.round3

Steps: exact per-level curves 2024-10-20..2026-10-31 start flat (Pool(2), float32, hourly)
-> LP on the 1% curves, DAY=300 floor $800, full pool and live-only pool -> exact greedy
re-size at discrete levels -> pairwise swap local search (full pool) -> close-all replay at
-$300 (slip $25), 2 years and last 12 months from a fresh start -> comparison vs the live 66
as deployed -> data-artefact flags -> JSON for the report + docs/board/portfolio-round3.json.
"""
import os, sys, json, time
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool
import numpy as np, pandas as pd
from research.search2.portfolio import core as P
from research.search2.portfolio.improve import swap_search
from research.search3.portfolio import core3 as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
LIVE = "docs/board/portfolio-lp300-66.json"
CACHE = os.path.join(OUT, "level_curves.npz")


def build_pool():
    pool = []
    for m in json.load(open(LIVE))["mix"]:
        m = dict(m); m["key"] = P.keyof(m); m["src"] = "live66"; m["group"] = "live"; pool.append(m)
    seen = {m["key"] for m in pool}
    for s in json.load(open(os.path.join(HERE, "pool_a.json"))):
        s = dict(s); s["fn"] = s["build_fn"]; s["family"] = "r3_" + s["group"]; s["key"] = P.keyof(s); s["src"] = "new"
        if s["key"] not in seen:
            pool.append(s); seen.add(s["key"])
    return pool


def sims(jobs, label):
    t0 = time.time()
    with Pool(2, maxtasksperchild=60) as pp:
        res = list(pp.imap(C.run, jobs, chunksize=4))
    print(f"{label}: {len(jobs)} sims in {time.time() - t0:.0f}s", flush=True)
    return res


def level_curves(pool, start, end):
    L = len(P.LEVELS)
    if os.path.exists(CACHE):
        z = np.load(CACHE, allow_pickle=True)
        idx, Cc, W = pd.DatetimeIndex(z["idx"]), z["C"], z["W"]
        trades = [[pd.read_pickle(os.path.join(OUT, f"tr_{i}_{l}.pkl")) for l in range(L)] for i in range(len(pool))]
        print("level curves loaded from cache", flush=True)
        return idx, Cc, W, trades
    jobs = [(x, r, start, end) for x in pool for r in P.LEVELS]
    res = sims(jobs, f"per-level {start:%Y-%m-%d}..{end:%Y-%m-%d}")
    hw, hc = zip(*[P.hourly(cv) for _, cv, _ in res])
    idx, Cc, W = P.stack(list(hw), list(hc))
    n = len(pool)
    Cc = Cc.reshape(n, L, -1); W = W.reshape(n, L, -1)
    trades = [[res[i * L + l][2] for l in range(L)] for i in range(n)]
    np.savez(CACHE, idx=idx.values, C=Cc, W=W)
    for i in range(n):
        for l in range(L):
            trades[i][l].to_pickle(os.path.join(OUT, f"tr_{i}_{l}.pkl"))
    return idx, Cc, W, trades


def summarize_mix(pool, lvl, idx, Cc, W, trades, label):
    chosen = [i for i in range(len(pool)) if lvl[i] >= 0]
    c = sum(Cc[i, lvl[i]] for i in chosen).astype(float); w = sum(W[i, lvl[i]] for i in chosen).astype(float)
    tr = {pool[i]["key"]: trades[i][lvl[i]] for i in chosen}
    mon, summ = P.report(label, idx, c, w, tr)
    summ["max_open_risk"] = P.open_risk(tr, {pool[i]["key"]: P.LEVELS[lvl[i]] for i in chosen})
    summ["n_strategies"] = len(chosen)
    summ["n_new"] = sum(pool[i]["src"] == "new" for i in chosen)
    print(f"lowest equity ${summ['lowest_equity']:,.0f} | max $ at risk at once ${summ['max_open_risk']:,.0f} | "
          f"{len(chosen)} strategies ({summ['n_new']} new)", flush=True)
    per = {}
    mix = []
    for i in chosen:
        t = trades[i][lvl[i]]
        net_i = float(Cc[i, lvl[i], -1])
        big = float(t.profit.abs().max()) if len(t) else 0.0
        per[f"{pool[i]['name']} {pool[i]['symbol']} {pool[i]['tf']}"] = round(net_i)
        mix.append(dict(name=pool[i]["name"], symbol=pool[i]["symbol"], tf=pool[i]["tf"], family=pool[i]["family"],
                        module=pool[i]["module"], fn=pool[i]["fn"], params=pool[i]["params"], risk=P.LEVELS[lvl[i]],
                        src=pool[i]["src"], group=pool[i]["group"], net_2y=round(net_i), trades_2y=int(len(t)),
                        biggest_trade=round(big), biggest_share=(round(big / abs(net_i), 2) if net_i else None),
                        max_lots=(float(t.lots.max()) if len(t) else 0.0),
                        first_trade=(str(t.entry_time.min())[:10] if len(t) else None),
                        old_avg_month=pool[i].get("old_avg_month", pool[i].get("avg_month"))))
    return dict(mix=mix, summary=summ, monthly=mon, per_strategy=per), tr


def main():
    pool = build_pool(); n = len(pool)
    live_idx = [i for i in range(n) if pool[i]["src"] == "live66"]
    new_idx = [i for i in range(n) if pool[i]["src"] == "new"]
    print(f"pool: {n} strategies ({len(live_idx)} live + {len(new_idx)} new)", flush=True)

    idx, Cc, W, trades = level_curves(pool, C.START, C.END)
    L = len(P.LEVELS); l1 = P.LEVELS.index(0.01)
    C1, W1 = Cc[:, l1, :], W[:, l1, :]
    # per-strategy 1% facts for the ranked table
    first = P.day_first(idx)
    solo = {}
    for i in range(n):
        c = C1[i].astype(float); w = W1[i].astype(float)
        dd, wd = P.metrics(idx, c, w)
        t = trades[i][l1]
        big = float(t.profit.abs().max()) if len(t) else 0.0
        solo[pool[i]["key"]] = dict(net_1pct=round(float(c[-1])), worst_day_1pct=round(wd), max_dd_1pct=round(dd),
                                   trades_1pct=int(len(t)), biggest_share_1pct=(round(big / abs(c[-1]), 2) if c[-1] else None),
                                   max_lots_1pct=(float(t.lots.max()) if len(t) else 0.0))

    # eligibility: at least MIN_TRADES trades at 1% over the window (a strategy with 1-2 winning trades
    # otherwise gets sized to 3% because it never lost; that is luck, not an edge)
    MIN_TRADES = 10
    elig = [i for i in range(n) if solo[pool[i]["key"]]["trades_1pct"] >= MIN_TRADES]
    print(f"eligible (>= {MIN_TRADES} trades at 1%): {len(elig)} of {n}; excluded: "
          f"{[(pool[i]['name'], pool[i]['symbol'], solo[pool[i]['key']]['trades_1pct']) for i in range(n) if i not in elig]}")
    results0 = dict(ineligible=[dict(name=pool[i]["name"], symbol=pool[i]["symbol"], tf=pool[i]["tf"], src=pool[i]["src"],
                                     trades_1pct=solo[pool[i]["key"]]["trades_1pct"]) for i in range(n) if i not in elig])
    live_el = [i for i in live_idx if i in elig]
    print("\nLP full pool:"); w_e, net_e = P.lp(idx, C1[elig], W1[elig])
    w_full = np.zeros(n); w_full[elig] = w_e; net = np.zeros(n); net[elig] = net_e
    print("\nLP live-66 only:"); w_live, _ = P.lp(idx, C1[live_el], W1[live_el])
    pick_full = [i for i in range(n) if w_full[i] > 0.02]
    pick_live = [live_el[j] for j in range(len(live_el)) if w_live[j] > 0.02]
    print(f"LP full picked {len(pick_full)} ({sum(pool[i]['src']=='new' for i in pick_full)} new), est ${w_full @ net:,.0f}")
    print(f"LP live-only picked {len(pick_live)}, est ${w_live @ net[live_el]:,.0f}")

    results = dict(**results0, lp_weights={pool[i]["key"]: float(w_full[i]) for i in range(n)}, solo=solo,
                   pool=[{k: pool[i][k] for k in ("name", "symbol", "tf", "module", "fn", "params", "src", "group", "key")} for i in range(n)])
    # exact greedy from the LP picks, then a pairwise swap local search over the whole pool
    def repair(lvl0, allowed):
        """Lower one level at a time (the cut that most improves the binding cap) until the caps hold."""
        lvl = lvl0.copy(); T = Cc.shape[2]
        cur = lambda i, l: (np.zeros(T), np.zeros(T)) if l < 0 else (Cc[i, l].astype(float), W[i, l].astype(float))
        def slack(c, w):
            prev = np.r_[0.0, c[:-1]]
            return min(w.min() + P.FLOOR, (w - prev[first]).min() + P.DAY)
        c = sum(cur(i, lvl[i])[0] for i in range(n)); w = sum(cur(i, lvl[i])[1] for i in range(n))
        cuts = 0
        while slack(c, w) <= 0:
            best = None
            for i in range(n):
                if lvl[i] < 0 or (allowed is not None and i not in allowed): continue
                dc = cur(i, lvl[i] - 1)[0] - cur(i, lvl[i])[0]; dw = cur(i, lvl[i] - 1)[1] - cur(i, lvl[i])[1]
                sl = slack(c + dc, w + dw)
                if best is None or sl > best[0]: best = (sl, i, dc, dw)
            _, i, dc, dw = best; lvl[i] -= 1; c += dc; w += dw; cuts += 1
        return lvl, cuts

    def lp_round_start(wv, allowed):
        """Nearest discrete level to the LP weight (1% units), then repair."""
        lv = np.full(n, -1)
        for i in allowed:
            r = wv[i] / 100.0
            if r >= P.LEVELS[0] / 2:
                lv[i] = int(np.argmin([abs(r - L_) for L_ in P.LEVELS]))
        return repair(lv, set(allowed))

    def optimise(allowed, label):
        """Three starts (LP->greedy, LP rounded+repaired, empty greedy over all allowed), each polished by the
        pairwise swap search; the best net wins."""
        allowed = set(allowed); outs = []
        lp_pick = [i for i in allowed if w_full[i] > 0.02] if allowed != set(live_el) else pick_live
        lg, _, _ = P.exact_greedy(idx, Cc, W, allowed=lp_pick); ls, m1 = swap_search(idx, Cc, W, lg, allowed, max_iter=300)
        outs.append((f"LP->greedy->swap ({m1} moves)", ls))
        wv = w_full if allowed != set(live_el) else np.r_[w_live][np.argsort(np.argsort(live_el))] if False else None
        if wv is None:
            wv = np.zeros(n); wv[live_el] = w_live
        lr, cuts = lp_round_start(wv, lp_pick); lrs, m2 = swap_search(idx, Cc, W, lr, allowed, max_iter=300)
        outs.append((f"LP rounded ({cuts} cuts)->swap ({m2} moves)", lrs))
        ga, _, _ = P.exact_greedy(idx, Cc, W, allowed=allowed); gas, m3 = swap_search(idx, Cc, W, ga, allowed, max_iter=300)
        outs.append((f"greedy all->swap ({m3} moves)", gas))
        for lab, lv in outs:
            c = sum(Cc[i, lv[i]] for i in range(n) if lv[i] >= 0)
            print(f"  {label}: {lab}: net ${float(c[-1]) if len(c) else 0:,.0f}")
        lab, lv = max(outs, key=lambda o: float(sum(Cc[i, o[1][i], -1] for i in range(n) if o[1][i] >= 0)) if any(o[1] >= 0) else -1e9)
        print(f"  {label}: best start = {lab}")
        return lv

    lvl_s = optimise(elig, "full pool")
    results["new"], tr_new = summarize_mix(pool, lvl_s, idx, Cc, W, trades, "NEW MIX (full pool, best of three starts + swap search)")
    lvl_ls = optimise(live_el, "live only")
    results["re66"], _ = summarize_mix(pool, lvl_ls, idx, Cc, W, trades, "RE-OPTIMISED 66 ONLY (same method, no new strategies)")
    # current live mix as deployed
    lvl_cur = np.full(n, -1)
    for i in live_idx: lvl_cur[i] = P.LEVELS.index(pool[i]["risk"])
    results["current"], tr_cur = summarize_mix(pool, lvl_cur, idx, Cc, W, trades, "CURRENT LIVE 66 (as deployed)")
    # swap search starting from the live levels (repaired first) with the full pool, the round-2 route, for reference
    lvl_rep, cuts = repair(lvl_cur, None)
    lvl_sl, mv3 = swap_search(idx, Cc, W, lvl_rep, set(elig), max_iter=300)
    results["swap_from_live"], _ = summarize_mix(pool, lvl_sl, idx, Cc, W, trades, f"SWAP FROM LIVE LEVELS ({cuts} repair cuts), full pool ({mv3} moves)")
    if results["swap_from_live"]["summary"]["net"] > results["new"]["summary"]["net"]:
        print("swap-from-live beats the fresh build -> using it as the new mix")
        results["new_alt"] = results["new"]; results["new"] = results["swap_from_live"]; lvl_s = lvl_sl
    else:
        results["new_alt"] = results["swap_from_live"]
    results["new_levels"] = {pool[i]["key"]: (P.LEVELS[lvl_s[i]] if lvl_s[i] >= 0 else 0.0) for i in range(n)}
    results["dropped_live"] = [dict(name=pool[i]["name"], symbol=pool[i]["symbol"], tf=pool[i]["tf"], old_risk=pool[i]["risk"])
                               for i in live_idx if lvl_s[i] < 0]
    results["kept_live_changed"] = [dict(name=pool[i]["name"], symbol=pool[i]["symbol"], tf=pool[i]["tf"], old_risk=pool[i]["risk"],
                                         new_risk=P.LEVELS[lvl_s[i]]) for i in live_idx if lvl_s[i] >= 0 and P.LEVELS[lvl_s[i]] != pool[i]["risk"]]
    results["new_in"] = [dict(name=pool[i]["name"], symbol=pool[i]["symbol"], tf=pool[i]["tf"], group=pool[i]["group"], risk=P.LEVELS[lvl_s[i]])
                         for i in new_idx if lvl_s[i] >= 0]
    del Cc, W

    # close-all replays: 2 years and last 12 months from a fresh start
    def mix_runs(res, start, end):
        strat = {x["key"]: x for x in pool}
        return sims([(strat[P.keyof(m)], m["risk"], start, end) for m in res["mix"]], f"replay sims {start:%Y-%m-%d}")
    results["replay"] = {}
    for lab in ("current", "new"):
        results["replay"][lab] = dict(last2=P.replay(mix_runs(results[lab], C.START, C.END), f"{lab} 2y"),
                                      last12=P.replay(mix_runs(results[lab], C.LAST12, C.END), f"{lab} last 12m"))
    json.dump(results, open(os.path.join(OUT, "round3_results.json"), "w"), indent=1, default=str)
    board = dict(mix=results["new"]["mix"],
                 last2=dict(summary=results["new"]["summary"], monthly=results["new"]["monthly"], per_strategy=results["new"]["per_strategy"]),
                 replay_close_all_300=results["replay"]["new"],
                 vs_current66=dict(last2=results["current"]["summary"], replay=results["replay"]["current"]),
                 re66=dict(summary=results["re66"]["summary"]),
                 note="Round 3 (2026-10-30): full pool = 80 new per-market candidates + the live 66, no preference for the current mix. "
                      "Curves 2024-10-20..2026-10-31 start flat, 6000-bar warmup, LP DAY=300 floor $9,200 on 1% curves, exact per-level greedy, "
                      "pairwise swap search over the whole pool, close-all stop -$300 slip $25 replayed. Group cost patches and data cleaners applied.")
    json.dump(board, open("docs/board/portfolio-round3.json", "w"), indent=1, default=str)
    print("\nDONE ->", os.path.join(OUT, "round3_results.json"), "and docs/board/portfolio-round3.json")


if __name__ == "__main__":
    main()
