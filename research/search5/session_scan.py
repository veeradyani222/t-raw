"""Round-5 new family: time-of-day holds ("buy at the close of hour A, sell at the close of
hour B, every day") per market, picked on dev data (before 2023-10-20) ONLY, then judged
on the unseen years with the real harness (stop 3 ATR, time exit).

    cd mt5-trader && .venv/Scripts/python.exe -m research.search5.session_scan

Step 1 (vectorised, dev data): for every market with H1 bars from 2019 or earlier and every
(h_in, h_out) pair, the per-day $ P&L of a 1-lot hold after spread/slippage/commission.
Keep pairs with t-stat >= T_MIN, >= 70% green dev years, >= 4 dev years, and a plateau
(the mean t of the 8 neighbouring hour pairs >= PLAT_MIN). Best pair per market and side.
Step 2: the survivors as build_session_hold entries, simulated 2015..2026 at 1% with
the round-3 judge; dev vs unseen tables.
Writes out/session_scan.json, out/session_picks.json (pool entries for build_mix).
"""
import os, sys, json, time
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool
import numpy as np, pandas as pd
from research.prop import harness as H
from research.search3.portfolio import core3 as C3
from research.search3.portfolio.round3w import MGROUP
from research.search2.portfolio import core as P
from research.search5 import core5 as K

T_MIN, PLAT_MIN, MIN_YEARS, MIN_GREEN, MIN_TRADES = 3.0, 1.5, 4, 0.7, 300
MARKETS = ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "US500", "US30", "USTEC", "US2000", "DE40", "UK100", "FRA40", "ESP35", "STOXX50", "SWI20", "IT40",
           "JPN225", "HK50", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "EURGBP", "EURCHF", "EURJPY", "GBPJPY", "CHFJPY",
           "NZDJPY", "AUDNZD", "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPNZD", "XTIUSD", "XBRUSD", "XNGUSD", "BTCUSD", "ETHUSD", "LTCUSD"]


def cost_per_lot(sym, df):
    spec = H._spec().get(sym, {})
    contract = float(spec.get("contract", 100.0 if sym == "XAUUSD" else 100000.0))
    point = float(spec.get("point", 0.01))
    spread = max(H.SPREAD_FLOOR.get(sym, 0.0), float(np.nanmedian(df.spread.to_numpy(float)) * point) if "spread" in df else 0.0)
    slip = 0.1 * H._pip(sym)
    comm = 0.0 if sym in H.INDICES else H.COMMISSION_RT
    return contract, spread + 2 * slip, comm


def scan_market(sym):
    C3.patch_all()
    try:
        df = H.load(sym, "H1", split="all")
    except FileNotFoundError:
        return sym, None
    df = df[df.time < K.DEV_END].reset_index(drop=True)
    if sym in C3.CRYPTO:
        df = df[df.time.dt.weekday < 5].reset_index(drop=True)      # FundedNext: no weekend crypto bars
    if len(df) < 5000 or df.time.min() > pd.Timestamp("2019-07-01"):
        return sym, None
    contract, cost_px, comm = cost_per_lot(sym, df)
    day = df.time.dt.normalize(); hour = df.time.dt.hour.to_numpy()
    # close-by-hour matrix: one row per day, 24 columns (NaN when the hour has no bar)
    piv = pd.DataFrame({"d": day, "h": hour, "c": df.close.to_numpy(float), "conv": df.conv.to_numpy(float)})
    cm = piv.pivot_table(index="d", columns="h", values="c", aggfunc="last").reindex(columns=range(24))
    cv = piv.groupby("d").conv.median()
    close = cm.to_numpy(); days = cm.index; conv = cv.reindex(days).to_numpy()
    nd = len(days); years = days.year.to_numpy()
    out = []
    for h_in in range(24):
        for h_out in range(24):
            if h_out == h_in:
                continue
            if h_out > h_in:
                move = close[:, h_out] - close[:, h_in]
            else:   # overnight: exit next day's h_out
                move = np.r_[close[1:, h_out], np.nan] - close[:, h_in]
            pnl = move * contract * conv - cost_px * contract * conv - comm       # long, 1 lot
            ok = np.isfinite(pnl)
            if ok.sum() < MIN_TRADES:
                continue
            for side, sgn in (("long", 1.0), ("short", -1.0)):
                p = sgn * (move * contract * conv) - cost_px * contract * conv - comm
                p = p[ok]; yy = years[ok]
                mean, sd = p.mean(), p.std(ddof=1)
                t = mean / (sd / np.sqrt(len(p))) if sd > 0 else 0.0
                by = pd.Series(p).groupby(yy).sum()
                out.append(dict(symbol=sym, side=side, h_in=h_in, h_out=h_out, n=int(len(p)), mean=float(mean), t=float(t),
                                years=int(len(by)), green=float((by > 0).mean()), yearly={int(k): round(float(v)) for k, v in by.items()}))
    return sym, out


def plateau(rows):
    T = {(r["side"], r["h_in"], r["h_out"]): r["t"] for r in rows}
    for r in rows:
        nb = [T.get((r["side"], (r["h_in"] + a) % 24, (r["h_out"] + b) % 24)) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
        nb = [v for v in nb if v is not None]
        r["plateau_t"] = float(np.mean(nb)) if nb else 0.0
    return rows


def main():
    t0 = time.time()
    with Pool(2, maxtasksperchild=10) as pp:
        res = dict(pp.imap_unordered(scan_market, MARKETS))
    print(f"scan: {sum(v is not None for v in res.values())} markets in {time.time() - t0:.0f}s", flush=True)
    picks = []; all_rows = []
    for sym, rows in res.items():
        if not rows:
            continue
        rows = plateau(rows); all_rows += rows
        good = [r for r in rows if r["t"] >= T_MIN and r["years"] >= MIN_YEARS and r["green"] >= MIN_GREEN and r["plateau_t"] >= PLAT_MIN]
        for side in ("long", "short"):
            g = sorted([r for r in good if r["side"] == side], key=lambda r: -r["t"])
            if g:
                picks.append(g[0])
    print(f"{len(all_rows)} hour pairs tested, {len(picks)} picks (best per market and side):")
    for r in sorted(picks, key=lambda r: -r["t"]):
        print(f"  {r['symbol']:7} {r['side']:5} {r['h_in']:2d}->{r['h_out']:2d}  t={r['t']:.1f} plateau={r['plateau_t']:.1f} green {r['green']:.0%} of {r['years']}y  n={r['n']}")
    json.dump(dict(picks=picks, n_tested=len(all_rows), markets=sorted(k for k, v in res.items() if v)),
              open(os.path.join(K.OUT, "session_scan.json"), "w"), indent=1)
    # step 2: real harness, full history at 1%
    entries = []
    for r in picks:
        x = dict(name=f"tod_{r['side']}_{r['h_in']}-{r['h_out']}", symbol=r["symbol"], tf="H1", module="research.search3.metals.strategies",
                 fn="build_session_hold", params=dict(side=r["side"], h_in=r["h_in"], h_out=r["h_out"], stop_atr=3.0, max_hold=30),
                 group=MGROUP.get(r["symbol"], "live"), family="r5_tod", src="r5_tod", mixes=[], live_risk=None, mgroup=MGROUP.get(r["symbol"], "other"))
        x["key"] = P.keyof(x); entries.append(x)
    with Pool(2, maxtasksperchild=10) as pp:
        sims = list(pp.imap(C3.run, [(x, 0.01, K.START, K.END) for x in entries]))
    table = []
    for x, (_, cv, t) in zip(entries, sims):
        hw, hc = P.hourly(cv)
        w = hw.reindex(K.IDX).ffill().fillna(0).to_numpy(np.float32); c = hc.reindex(K.IDX).ffill().fillna(0).to_numpy(np.float32)
        x["i"] = -1
        s = K.strat_stats(x, c, w, t); s["key"] = x["key"]; table.append(s)
        np.savez_compressed(os.path.join(K.OUT, f"tod_{x['key'].replace('|', '_').replace('/', '_')[:80]}.npz"), w=w, c=c)
    df = pd.DataFrame(table)
    cols = ["name", "symbol", "first_trade", "years_dev", "pos_years_dev", "dev_pm", "y1_pm", "last2_pm", "sepoct_pm", "unseen3_worst_day", "unseen3_trades"]
    pd.set_option("display.width", 200)
    print(df[cols].round(0).sort_values("dev_pm", ascending=False).to_string(index=False))
    keep = df[(df.y1_pm > 0)]
    print(f"\nprofitable in the unseen year: {len(keep)}/{len(df)}; sum $/mo at 1%: dev {df.dev_pm.sum():,.0f}, unseen yr {df.y1_pm.sum():,.0f}, "
          f"last 2y {df.last2_pm.sum():,.0f}, Sep+Oct {df.sepoct_pm.sum():,.0f}")
    json.dump(dict(entries=entries, stats=table), open(os.path.join(K.OUT, "session_picks.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
