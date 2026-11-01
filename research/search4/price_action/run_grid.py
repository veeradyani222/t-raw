"""Round-4 grid: every price-action family x params on every market and timeframe,
full history, 1% risk, one job per (symbol, timeframe).

    .venv/Scripts/python.exe -m research.search4.price_action.run_grid OUT_DIR

Writes OUT_DIR/grid_<SYMBOL>_<TF>.pkl (list of dicts: symbol, tf, fam, params, trades).
Selection happens later, on trades closed before DEV_END only.
"""
import os, sys, time
os.environ.setdefault("PROP_OOS", "1")
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool

import pandas as pd

MARKETS = ("AUDNZD AUDUSD CHFJPY EURAUD EURCAD EURCHF EURGBP EURJPY EURNZD GBPAUD GBPJPY GBPNZD GBPUSD "
           "NZDJPY NZDUSD USDCAD USDCHF USDJPY EURUSD "
           "XAUUSD XAGUSD XPTUSD XPDUSD XTIUSD XBRUSD XNGUSD "
           "DE40 F40 HK50 IT40 JP225 STOXX50 SWI20 UK100 US2000 US30 US500 ESP35 USTEC "
           "BTCUSD ETHUSD LTCUSD ADAUSD BNBUSD DOTUSD").split()
TFS = ("M30", "H1", "H4", "D1")
WARM_BARS = 300
KEEP = ["entry_time", "exit_time", "side", "profit", "r", "reason"]


def job(args):
    sym, tf, out = args
    path = os.path.join(out, f"grid_{sym}_{tf}.pkl")
    if os.path.exists(path):
        return sym, tf, "cached", 0
    from research.prop import harness as H
    from research.search3.portfolio import core3 as C3
    from research.search3.portfolio.round3w import MGROUP
    from research.search4.price_action import strategies as S
    C3.patch_all()
    t0 = time.time()
    try:
        df = H.load(sym, tf, split="all")
    except Exception as e:                       # missing data / conversion pair
        pd.to_pickle([], path)
        return sym, tf, f"skip: {e}", 0
    df.attrs.update(symbol=sym, tf=tf, split="all", score_from=None)
    df = C3.group_clean(df, MGROUP.get(sym, "other"), sym)
    res = []
    for fam, grid in S.GRID.items():
        if fam in S.INTRADAY_ONLY and tf in ("H4", "D1"):
            continue
        fn = getattr(S, f"build_{fam}")
        for p in grid:
            sigs = fn(df, **p)
            sigs[:WARM_BARS] = [None] * WARM_BARS
            t = H.simulate(df, sigs, risk=0.01)["trades"]
            t = t[KEEP].copy() if len(t) else pd.DataFrame(columns=KEEP)
            res.append(dict(symbol=sym, tf=tf, fam=fam, params=p, trades=t))
    pd.to_pickle(res, path)
    return sym, tf, f"{len(res)} configs, {sum(len(r['trades']) for r in res)} trades", time.time() - t0


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    jobs = [(s, tf, out) for s in MARKETS for tf in TFS]
    t0 = time.time()
    with Pool(2, maxtasksperchild=8) as pp:
        for k, (s, tf, msg, dt) in enumerate(pp.imap_unordered(job, jobs), 1):
            print(f"[{k}/{len(jobs)}] {s} {tf}: {msg} ({dt:.0f}s) | {time.time() - t0:.0f}s total", flush=True)
