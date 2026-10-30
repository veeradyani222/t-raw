"""Round-3 portfolio build on THREE windows (2y / 3y / 5y) from the FULL pool
(80 new per-market candidates + the live 66), no preference for the current mix.

    cd mt5-trader && .venv/Scripts/python.exe -m research.search3.portfolio.round3w

Memory/disk are tight on this box (free RAM < 1 GB, disk < 700 MB), so unlike round3.py
this does NOT cache 146 x 9 per-level curves over five years. Instead:
  A. exact 1% simulations for every strategy 2021-10-20..now, start flat, 6000-bar warmup
     (Pool(2), hourly float32). Accounting is fixed-dollar risk, so a window from a later
     start is the same curve minus its value at the window start (only a position open
     across the boundary differs; noted, not material).
  B. per window: LP over the 1% curves (DAY=300, floor $800) -> candidate set (LP picks)
     -> exact per-level simulations for the candidates over that window only
     -> exact greedy / LP-rounded repair / swap search, best net wins.
  C. cross-evaluation: exact simulations at the chosen levels over the full five years
     for the three mixes and the live 66, then every window / calendar year is a fresh
     start slice, replayed with the live close-all stop at -$300 (slip $25).
Outputs: out/round3w_results.json, docs/board/portfolio-round3-{2y,3y,5y}.json.
"""
import os, sys, json, time, gc
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool
import numpy as np, pandas as pd
from research.search2.portfolio import core as P
from research.search2.portfolio.improve import swap_search
from research.search3.portfolio import core3 as C
from research.search3.portfolio.round3 import build_pool

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("R3W_OUT", os.path.join(HERE, "out")); os.makedirs(OUT, exist_ok=True)
SMOKE = int(os.environ.get("R3W_LIMIT", "0"))
END = pd.Timestamp("2026-10-31")
WINDOWS = {"5y": pd.Timestamp("2021-10-20"), "3y": pd.Timestamp("2023-10-20"), "2y": pd.Timestamp("2024-10-20")}
LAST12 = pd.Timestamp("2025-10-20")
START5 = WINDOWS["5y"]
YEARS = {y: (pd.Timestamp(f"{y}-01-01"), min(pd.Timestamp(f"{y + 1}-01-01"), END)) for y in (2022, 2023, 2024, 2025, 2026)}
L = len(P.LEVELS); l1 = P.LEVELS.index(0.01)
MIN_TRADES = 10

MGROUP = {}
for s in ("BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "SOLUSD", "ADAUSD", "BNBUSD", "DOTUSD"): MGROUP[s] = "crypto"
for s in ("XTIUSD", "XBRUSD", "XNGUSD"): MGROUP[s] = "oil_gas"
for s in ("JPN225", "JP225", "HK50", "AUS200", "CHINA50"): MGROUP[s] = "asia_indices"
for s in ("DE40", "FRA40", "F40", "ESP35", "UK100", "STOXX50", "SWI20", "IT40"): MGROUP[s] = "europe_indices"
for s in ("US30", "US500", "USTEC", "US2000"): MGROUP[s] = "us_indices"
for s in ("XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"): MGROUP[s] = "metals"
for s in ("USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "NZDJPY", "CADJPY"): MGROUP[s] = "jpy_crosses"
for s in ("AUDUSD", "NZDUSD", "USDCAD", "AUDNZD", "EURNZD", "GBPAUD", "GBPNZD", "EURAUD", "EURCAD", "GBPCAD", "AUDCAD",
          "AUDCHF", "CADCHF", "NZDCAD", "NZDCHF"): MGROUP[s] = "commodity_fx"
for s in ("USDZAR", "USDMXN", "USDNOK", "USDSEK", "EURNOK", "EURSEK", "USDSGD", "USDCNH", "USDPLN"): MGROUP[s] = "exotics"
for s in ("EURUSD", "GBPUSD", "USDCHF", "EURCHF", "GBPCHF", "EURGBP"): MGROUP[s] = "majors"


def sims(jobs, label):
    t0 = time.time()
    with Pool(2, maxtasksperchild=60) as pp:
        res = list(pp.imap(C.run, jobs, chunksize=4))
    print(f"{label}: {len(jobs)} sims in {time.time() - t0:.0f}s", flush=True)
    return res


def to_idx(idx, hw, hc):
    """Align hourly series to a given index (ffill, 0 before data)."""
    return (hw.reindex(idx).ffill().fillna(0).to_numpy(np.float32), hc.reindex(idx).ffill().fillna(0).to_numpy(np.float32))


def window_slice(idx, Cf, Wf, start, end=END):
    k = int(np.searchsorted(idx.values, start.to_datetime64())); k2 = int(np.searchsorted(idx.values, end.to_datetime64()))
    base = Cf[..., k - 1:k] if k > 0 else 0
    return idx[k:k2], Cf[..., k:k2] - base, Wf[..., k:k2] - base


def win_trades(t, start, end=END):
    if not len(t):
        return t
    return t[(t.entry_time >= start) & (t.entry_time < end)].reset_index(drop=True)


def strat_rec(x):
    return {k: x[k] for k in ("name", "symbol", "tf", "module", "fn", "params", "src", "group", "key")}


# --------------------------------------------------------------------------- step A
def one_pct(pool):
    cache = os.path.join(OUT, "r3w_1pct.npz"); tcache = os.path.join(OUT, "r3w_1pct_trades.pkl")
    if os.path.exists(cache) and os.path.exists(tcache):
        z = np.load(cache, allow_pickle=True)
        print("1% curves loaded from cache", flush=True)
        return pd.DatetimeIndex(z["idx"]), z["C"], z["W"], pd.read_pickle(tcache)
    res = sims([(x, 0.01, START5, END) for x in pool], "1% sims 2021-10-20..now")
    hw, hc = zip(*[P.hourly(cv) for _, cv, _ in res])
    idx, Cf, Wf = P.stack(list(hw), list(hc))
    trades = [r[2] for r in res]
    np.savez_compressed(cache, idx=idx.values, C=Cf, W=Wf); pd.to_pickle(trades, tcache)
    return idx, Cf, Wf, trades


# --------------------------------------------------------------------------- step B
def level_curves(pool, cand, idx_w, start, tag):
    cache = os.path.join(OUT, f"r3w_levels_{tag}.npz"); tcache = os.path.join(OUT, f"r3w_levels_{tag}_trades.pkl")
    if os.path.exists(cache) and os.path.exists(tcache):
        z = np.load(cache, allow_pickle=True)
        if list(z["cand"]) == list(cand):
            print(f"{tag}: per-level curves loaded from cache", flush=True)
            return z["C"], z["W"], pd.read_pickle(tcache)
    jobs = [(pool[i], r, start, END) for i in cand for r in P.LEVELS]
    res = sims(jobs, f"{tag} per-level {start:%Y-%m-%d}..now ({len(cand)} candidates)")
    m = len(cand); T = len(idx_w)
    Cc = np.zeros((m, L, T), np.float32); Wc = np.zeros_like(Cc); trades = [[None] * L for _ in range(m)]
    for j, (key, cv, t) in enumerate(res):
        hw, hc = P.hourly(cv)
        Wc[j // L, j % L], Cc[j // L, j % L] = to_idx(idx_w, hw, hc)
        trades[j // L][j % L] = t
    del res; gc.collect()
    np.savez_compressed(cache, cand=np.array(cand), C=Cc, W=Wc); pd.to_pickle(trades, tcache)
    return Cc, Wc, trades


def optimise(idx, Cc, Wc, w_lp, label):
    """Cc/Wc: (m, L, T) for the candidates; w_lp: LP weights (1% units) per candidate.
    Three starts (LP->greedy, LP rounded + repair, greedy all), each polished by the swap search."""
    m, _, T = Cc.shape; first = P.day_first(idx); allowed = set(range(m))
    cur = lambda i, l: (np.zeros(T), np.zeros(T)) if l < 0 else (Cc[i, l].astype(float), Wc[i, l].astype(float))

    def slack(c, w):
        prev = np.r_[0.0, c[:-1]]
        return min(w.min() + P.FLOOR, (w - prev[first]).min() + P.DAY)

    def repair(lvl0):
        lvl = lvl0.copy()
        c = sum(cur(i, lvl[i])[0] for i in range(m)); w = sum(cur(i, lvl[i])[1] for i in range(m)); cuts = 0
        while slack(c, w) <= 0:
            best = None
            for i in range(m):
                if lvl[i] < 0: continue
                dc = cur(i, lvl[i] - 1)[0] - cur(i, lvl[i])[0]; dw = cur(i, lvl[i] - 1)[1] - cur(i, lvl[i])[1]
                sl = slack(c + dc, w + dw)
                if best is None or sl > best[0]: best = (sl, i, dc, dw)
            _, i, dc, dw = best; lvl[i] -= 1; c += dc; w += dw; cuts += 1
        return lvl, cuts

    outs = []
    lp_pick = [i for i in range(m) if w_lp[i] > 0.02]
    lg, _, _ = P.exact_greedy(idx, Cc, Wc, allowed=lp_pick); ls, m1 = swap_search(idx, Cc, Wc, lg, allowed, max_iter=300)
    outs.append((f"LP->greedy->swap ({m1} moves)", ls))
    lv = np.full(m, -1)
    for i in lp_pick:
        r = w_lp[i] / 100.0
        if r >= P.LEVELS[0] / 2: lv[i] = int(np.argmin([abs(r - L_) for L_ in P.LEVELS]))
    lr, cuts = repair(lv); lrs, m2 = swap_search(idx, Cc, Wc, lr, allowed, max_iter=300)
    outs.append((f"LP rounded ({cuts} cuts)->swap ({m2} moves)", lrs))
    ga, _, _ = P.exact_greedy(idx, Cc, Wc, allowed=allowed); gas, m3 = swap_search(idx, Cc, Wc, ga, allowed, max_iter=300)
    outs.append((f"greedy all->swap ({m3} moves)", gas))
    netof = lambda lv: float(sum(Cc[i, lv[i], -1] for i in range(m) if lv[i] >= 0)) if (lv >= 0).any() else -1e9
    for lab, lv_ in outs:
        print(f"  {label}: {lab}: net ${netof(lv_):,.0f}", flush=True)
    lab, best = max(outs, key=lambda o: netof(o[1]))
    print(f"  {label}: best start = {lab}", flush=True)
    return best


def build_window(pool, tag, start, idx5, C1f, W1f, tr1):
    n = len(pool)
    idx, C1, W1 = window_slice(idx5, C1f, W1f, start)
    print(f"\n######## window {tag}: {start:%Y-%m-%d}..now, {len(idx)} hourly buckets", flush=True)
    solo = {}
    for i in range(n):
        c = C1[i].astype(float); w = W1[i].astype(float); dd, wd = P.metrics(idx, c, w)
        t = win_trades(tr1[i], start); big = float(t.profit.abs().max()) if len(t) else 0.0
        solo[pool[i]["key"]] = dict(net_1pct=round(float(c[-1])), worst_day_1pct=round(wd), max_dd_1pct=round(dd), trades_1pct=int(len(t)),
                                   biggest_share_1pct=(round(big / abs(c[-1]), 2) if c[-1] else None),
                                   max_lots_1pct=(float(t.lots.max()) if len(t) else 0.0),
                                   first_trade=(str(t.entry_time.min())[:10] if len(t) else None))
    elig = [i for i in range(n) if solo[pool[i]["key"]]["trades_1pct"] >= MIN_TRADES]
    print(f"eligible (>= {MIN_TRADES} trades at 1%): {len(elig)} of {n}", flush=True)
    print(f"LP full pool ({tag}):", flush=True)
    w_e, _ = P.lp(idx, C1[elig], W1[elig])
    w_full = np.zeros(n); w_full[elig] = w_e
    cand = sorted([i for i in elig if w_full[i] > 0.005], key=lambda i: -w_full[i])[:90]
    cand = sorted(cand)
    print(f"LP picked {sum(w_full[i] > 0.02 for i in elig)} (w>0.02); candidate set {len(cand)} "
          f"({sum(pool[i]['src'] == 'new' for i in cand)} new)", flush=True)
    Cc, Wc, trc = level_curves(pool, cand, idx, start, tag)
    lvl = optimise(idx, Cc, Wc, w_full[cand], f"{tag}")
    chosen = [j for j in range(len(cand)) if lvl[j] >= 0]
    c = sum(Cc[j, lvl[j]] for j in chosen).astype(float); w = sum(Wc[j, lvl[j]] for j in chosen).astype(float)
    trd = {pool[cand[j]]["key"]: trc[j][lvl[j]] for j in chosen}
    mon, summ = P.report(f"MIX-{tag} on its own window", idx, c, w, trd)
    summ["max_open_risk"] = P.open_risk(trd, {pool[cand[j]]["key"]: P.LEVELS[lvl[j]] for j in chosen})
    summ["n_strategies"] = len(chosen); summ["n_new"] = sum(pool[cand[j]]["src"] == "new" for j in chosen)
    print(f"lowest equity ${summ['lowest_equity']:,.0f} | max $ at risk at once ${summ['max_open_risk']:,.0f} | "
          f"{len(chosen)} strategies ({summ['n_new']} new)", flush=True)
    mix = []
    for j in chosen:
        x = pool[cand[j]]; t = trc[j][lvl[j]]; net_i = float(Cc[j, lvl[j], -1]); big = float(t.profit.abs().max()) if len(t) else 0.0
        mix.append(dict(name=x["name"], symbol=x["symbol"], tf=x["tf"], family=x["family"], module=x["module"], fn=x["fn"],
                        params=x["params"], risk=P.LEVELS[lvl[j]], src=x["src"], group=x["group"], mgroup=MGROUP.get(x["symbol"], "other"),
                        net_window=round(net_i), trades_window=int(len(t)), biggest_trade=round(big),
                        biggest_share=(round(big / abs(net_i), 2) if net_i else None), max_lots=(float(t.lots.max()) if len(t) else 0.0),
                        first_trade=(str(t.entry_time.min())[:10] if len(t) else None),
                        old_avg_month=x.get("old_avg_month", x.get("avg_month"))))
    out = dict(window=tag, start=str(start.date()), mix=mix, summary=summ, monthly=mon, solo=solo,
               lp_weights={pool[i]["key"]: float(w_full[i]) for i in range(n)}, candidates=[pool[i]["key"] for i in cand],
               ineligible=[dict(name=pool[i]["name"], symbol=pool[i]["symbol"], tf=pool[i]["tf"], src=pool[i]["src"],
                                trades_1pct=solo[pool[i]["key"]]["trades_1pct"]) for i in range(n) if i not in elig])
    del Cc, Wc, trc, C1, W1; gc.collect()
    return out


# --------------------------------------------------------------------------- step C
def cross_eval(pool, mixes, idx5):
    """mixes: {label: [mix entries with key+risk]}. Exact sims at the chosen level over five years, then
    every window / year as a fresh-start slice replayed with and without the close-all stop."""
    strat = {x["key"]: x for x in pool}
    need = sorted({(P.keyof(m), m["risk"]) for mx in mixes.values() for m in mx})
    res = sims([(strat[k], r, START5, END) for k, r in need], f"cross-eval sims ({len(need)} strategy/level pairs, 5y)")
    runs = {}
    for (k, r), (_, cv, t) in zip(need, res):
        hw, hc = P.hourly(cv); w, c = to_idx(idx5, hw, hc)
        runs[(k, r)] = (c, w, t)
    del res; gc.collect()
    spans = {"2y": (WINDOWS["2y"], END), "3y": (WINDOWS["3y"], END), "5y": (WINDOWS["5y"], END), "last12": (LAST12, END)}
    spans.update({str(y): se for y, se in YEARS.items()})
    table = {}; per_strat = {}
    for lab, mx in mixes.items():
        table[lab] = {}; per_strat[lab] = {}
        for sp, (s, e) in spans.items():
            k = int(np.searchsorted(idx5.values, s.to_datetime64())); k2 = int(np.searchsorted(idx5.values, e.to_datetime64()))
            idx = idx5[k:k2]
            rr = []; nets = {}; grp = {}
            for m in mx:
                c, w, t = runs[(P.keyof(m), m["risk"])]
                base = float(c[k - 1]) if k > 0 else 0.0
                cv = pd.DataFrame({"time": idx, "worst": (w[k:k2] - base).astype(float), "close": (c[k:k2] - base).astype(float)})
                tw = win_trades(t, s, e)
                rr.append((P.keyof(m), cv, tw))
                nets[f"{m['name']} {m['symbol']} {m['tf']}"] = round(float(c[k2 - 1] - base)) if k2 > k else 0
                g = MGROUP.get(m["symbol"], "other"); grp[g] = grp.get(g, 0) + nets[f"{m['name']} {m['symbol']} {m['tf']}"]
            rep = P.replay(rr, f"{lab} / {sp}")
            risks = {P.keyof(m): m["risk"] for m in mx}
            rep["max_open_risk"] = P.open_risk({kk: tw for kk, _, tw in rr}, risks)
            rep["by_group"] = {g: round(v) for g, v in sorted(grp.items(), key=lambda kv: -kv[1])}
            rep["flat_before"] = sorted({f"{m['symbol']} {m['tf']}" for m in mx if len(runs[(P.keyof(m), m["risk"])][2])
                                         and runs[(P.keyof(m), m["risk"])][2].entry_time.min() > s + pd.Timedelta(days=60)})
            table[lab][sp] = rep; per_strat[lab][sp] = nets
    return table, per_strat


def flags_for(mix, table_lab):
    fl = []
    tot = sum(m["net_window"] for m in mix) or 1
    for m in mix:
        tag = f"{m['name']} {m['symbol']} {m['tf']} @{m['risk']:.2%}"
        if m["biggest_share"] is not None and m["biggest_share"] > 0.35 and m["net_window"] > 0:
            fl.append(f"{tag}: one trade is {m['biggest_share']:.0%} of its profit (${m['biggest_trade']})")
        if m["trades_window"] < 15:
            fl.append(f"{tag}: only {m['trades_window']} trades in the window")
        if m["max_lots"] >= 5:
            fl.append(f"{tag}: max lots {m['max_lots']:.2f}")
        if m["net_window"] / tot > 0.25:
            fl.append(f"{tag}: {m['net_window'] / tot:.0%} of the mix profit")
    return fl


def main():
    pool = build_pool()
    if SMOKE:
        pool = pool[:SMOKE // 2] + pool[-SMOKE // 2:]
    n = len(pool)
    live_idx = [i for i in range(n) if pool[i]["src"] == "live66"]
    print(f"pool: {n} strategies ({len(live_idx)} live + {n - len(live_idx)} new)", flush=True)
    idx5, C1f, W1f, tr1 = one_pct(pool)
    print(f"five-year hourly index: {len(idx5)} buckets {idx5[0]}..{idx5[-1]}", flush=True)
    data_start = {f"{pool[i]['symbol']} {pool[i]['tf']}": (str(tr1[i].entry_time.min())[:10] if len(tr1[i]) else None) for i in range(n)}

    results = dict(pool=[strat_rec(x) for x in pool], windows={}, data_first_trade=data_start)
    for tag in ("2y", "3y", "5y"):
        rp = os.path.join(OUT, f"r3w_window_{tag}.json")
        if os.path.exists(rp):
            results["windows"][tag] = json.load(open(rp)); print(f"window {tag} loaded from cache", flush=True)
            continue
        results["windows"][tag] = build_window(pool, tag, WINDOWS[tag], idx5, C1f, W1f, tr1)
        json.dump(results["windows"][tag], open(rp, "w"), indent=1, default=str)
    del C1f, W1f; gc.collect()

    mixes = {"current66": [dict(pool[i], risk=pool[i]["risk"], net_window=0) for i in live_idx]}
    for tag in ("2y", "3y", "5y"):
        mixes[f"mix_{tag}"] = [dict(m, key=P.keyof(m)) for m in results["windows"][tag]["mix"]]
    for m in mixes["current66"]:
        m["key"] = P.keyof(m)
    table, per_strat = cross_eval(pool, mixes, idx5)
    results["cross"] = table; results["cross_per_strategy"] = per_strat
    live_keys = {pool[i]["key"]: pool[i] for i in live_idx}
    for tag in ("2y", "3y", "5y"):
        W_ = results["windows"][tag]; keys = {P.keyof(m) for m in W_["mix"]}
        W_["new_in"] = [dict(name=m["name"], symbol=m["symbol"], tf=m["tf"], group=m["group"], risk=m["risk"]) for m in W_["mix"] if m["src"] == "new"]
        W_["dropped_live"] = [dict(name=x["name"], symbol=x["symbol"], tf=x["tf"], old_risk=x["risk"]) for k, x in live_keys.items() if k not in keys]
        W_["kept_live_changed"] = [dict(name=m["name"], symbol=m["symbol"], tf=m["tf"], old_risk=live_keys[P.keyof(m)]["risk"], new_risk=m["risk"])
                                   for m in W_["mix"] if m["src"] == "live66" and live_keys[P.keyof(m)]["risk"] != m["risk"]]
        W_["flags"] = flags_for(W_["mix"], table[f"mix_{tag}"])
    json.dump(results, open(os.path.join(OUT, "round3w_results.json"), "w"), indent=1, default=str)
    for tag in ("2y", "3y", "5y"):
        W_ = results["windows"][tag]
        board = dict(mix=[{k: v for k, v in m.items() if k != "key"} for m in W_["mix"]],
                     window=dict(tag=tag, start=W_["start"], end=str(END.date()), summary=W_["summary"], monthly=W_["monthly"]),
                     cross_eval={lab: {sp: dict(close_all=rep["close_all"]["summary"], no_stop=rep["no_stop"]["summary"],
                                                max_open_risk=rep["max_open_risk"], by_group=rep["by_group"])
                                       for sp, rep in table[lab].items()} for lab in table},
                     new_in=W_["new_in"], dropped_live=W_["dropped_live"], kept_live_changed=W_["kept_live_changed"], flags=W_["flags"],
                     note=f"Round 3 (2026-10-30), window {tag} ({W_['start']}..2026-10-31): full pool = 80 new per-market candidates + the live 66, "
                          "no preference for the current mix. Exact sims start flat with 6000-bar warmup, hourly buckets, LP DAY=300 floor $9,200 "
                          "on 1% curves, exact per-level greedy + LP-rounded repair + pairwise swap search, close-all stop -$300 slip $25 replayed. "
                          "Group cost patches and data cleaners applied (core3.py). Fixed-dollar risk, not compounding.")
        json.dump(board, open(os.path.join(OUT, f"portfolio-round3-{tag}.json") if SMOKE else f"docs/board/portfolio-round3-{tag}.json", "w"), indent=1, default=str)
    print("\nDONE ->", os.path.join(OUT, "round3w_results.json"), flush=True)


if __name__ == "__main__":
    main()
