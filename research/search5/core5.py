"""Round-5 judge: honest, long-history scoring of every known strategy.

The round-3 pool (146 strategies: the live 66 + 80 round-3 candidates) is simulated ONCE
at 1% risk over the whole history we have (2015-01-01..2026-10-31) with the round-3
judge (research.search3.portfolio.core3.run: group cost patches, data cleaners, start
flat). Hourly worst/close curves (float32) and the trade lists are cached per strategy in
research/search5/out/full/ so every later step is a slice.

Periods (fixed-dollar risk => a period is the curve minus its value at the period start):
    dev     2015-01-01 .. 2023-10-20   the only data any round-5 pick may look at
    y1      2023-10-20 .. 2024-10-20   first unseen year
    last2   2024-10-20 .. 2026-10-31   last two years (the window the round-3 pool and
                                       the 66 were SEARCHED on, so for them this is a fit
                                       period, flagged in every table)
    sepoct  2026-09-01 .. 2026-10-31   the live months
    unseen3 2023-10-20 .. 2026-10-31   all three unseen years together

Accounts: $5K FundedNext Stellar Lite (risk fractions in the mix files are for $10K, so
x0.5; daily close-all at -$125 slip $12.5; floor -$400; a challenge start fails at -$400
before +$400) and the $10K equivalent (x1.0, -$300 / $25, floor -$800, -$800 before +$800).

    cd mt5-trader && .venv/Scripts/python.exe -m research.search5.core5      # build the cache
"""
import os, sys, json, time
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.getcwd())
from multiprocessing import Pool
import numpy as np, pandas as pd

from research.search2.portfolio import core as P
from research.search3.portfolio import core3 as C3
from research.search3.portfolio.round3 import build_pool as r3_pool
from research.search3.portfolio.round3w import MGROUP

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); FULL = os.path.join(OUT, "full")
os.makedirs(FULL, exist_ok=True)

START = pd.Timestamp("2015-01-01")
DEV_END = pd.Timestamp("2023-10-20")
Y1_END = pd.Timestamp("2024-10-20")
SO_START = pd.Timestamp("2026-09-01")
END = pd.Timestamp("2026-10-31")
PERIODS = {"dev": (START, DEV_END), "y1": (DEV_END, Y1_END), "last2": (Y1_END, END),
           "sepoct": (SO_START, END), "unseen3": (DEV_END, END)}
IDX = pd.date_range(START, END, freq="h", inclusive="left")

ACCTS = {
    "5k": dict(scale=0.5, halt=125.0, slip=12.5, floor=400.0, target=400.0, start_bal=5000.0, label="$5K (x0.5, stop -$125)"),
    "10k": dict(scale=1.0, halt=300.0, slip=25.0, floor=800.0, target=800.0, start_bal=10000.0, label="$10K (x1.0, stop -$300)"),
}
RISK_CAP = 0.0275          # per-trade cap in the live runner (fraction of the account)
NOT_OFFERED = {"SOLUSD"}   # FundedNext does not list it

MIX_FILES = {"24": "docs/board/portfolio-round3-24.json", "66": "docs/board/portfolio-lp300-66.json",
             "74": "docs/board/portfolio-round3.json", "51": "docs/board/portfolio-round3-2y.json",
             "62": "docs/board/portfolio-round3-3y.json", "57": "docs/board/portfolio-round3-5y.json"}


def build_pool():
    """Round-3 pool (146) tagged with the mixes each strategy sits in and its $10K risk in the live 24."""
    pool = r3_pool()
    tags = {}
    live_risk = {}
    for lab, path in MIX_FILES.items():
        for m in json.load(open(path))["mix"]:
            k = P.keyof(m); tags.setdefault(k, []).append(lab)
            if lab == "24":
                live_risk[k] = m["risk"]
    for i, x in enumerate(pool):
        x["i"] = i; x["mixes"] = tags.get(x["key"], []); x["live_risk"] = live_risk.get(x["key"])
        x["mgroup"] = MGROUP.get(x["symbol"], "other")
    return pool


# ------------------------------------------------------------------ full-history 1% cache
def _paths(i):
    return os.path.join(FULL, f"{i}.npz"), os.path.join(FULL, f"{i}_trades.pkl")


def full_run(x):
    pz, pt = _paths(x["i"])
    if os.path.exists(pz) and os.path.exists(pt):
        return x["i"], "cached"
    t0 = time.time()
    try:
        _, cv, t = C3.run((x, 0.01, START, END))
    except Exception as e:  # noqa: BLE001  one bad strategy must not kill the batch
        return x["i"], f"ERROR {type(e).__name__}: {e}"
    hw, hc = P.hourly(cv)
    w = hw.reindex(IDX).ffill().fillna(0).to_numpy(np.float32)
    c = hc.reindex(IDX).ffill().fillna(0).to_numpy(np.float32)
    np.savez_compressed(pz, w=w, c=c)
    cols = ["entry_time", "exit_time", "profit", "lots"]
    (t[cols] if len(t) else pd.DataFrame(columns=cols)).to_pickle(pt)
    return x["i"], f"{len(t)} trades in {time.time() - t0:.0f}s"


def build_cache(pool, workers=2):
    todo = [x for x in pool if not all(os.path.exists(p) for p in _paths(x["i"]))]
    print(f"full-history 1% sims: {len(todo)} to run, {len(pool) - len(todo)} cached", flush=True)
    t0 = time.time()
    with Pool(workers, maxtasksperchild=20) as pp:
        for i, msg in pp.imap_unordered(full_run, todo, chunksize=1):
            print(f"  [{i:3d}] {pool[i]['name']} {pool[i]['symbol']} {pool[i]['tf']}: {msg}", flush=True)
    print(f"done in {time.time() - t0:.0f}s", flush=True)


def load_full(pool):
    """-> C (n, T) float32 close curves at 1%, W (n, T) worst, trades list."""
    n = len(pool); T = len(IDX)
    C = np.zeros((n, T), np.float32); W = np.zeros((n, T), np.float32); trades = [None] * n
    for x in pool:
        pz, pt = _paths(x["i"])
        if not os.path.exists(pz):
            continue
        z = np.load(pz); C[x["i"]] = z["c"]; W[x["i"]] = z["w"]; trades[x["i"]] = pd.read_pickle(pt)
    return C, W, trades


# ------------------------------------------------------------------ period slices and statistics
def pos(ts):
    return int(np.searchsorted(IDX.values, pd.Timestamp(ts).to_datetime64()))


def seg(c, start, end):
    """Curve over [start, end) re-based to 0 at the start."""
    k, k2 = pos(start), pos(end)
    base = c[..., k - 1:k] if k > 0 else 0
    return IDX[k:k2], c[..., k:k2] - base


def months_in(start, end):
    return max((pd.Timestamp(end) - pd.Timestamp(start)).days / 30.44, 1e-9)


def yearly(c, first_trade):
    """Calendar-year P&L at 1% for every year the strategy was trading from (near) its start."""
    out = {}
    if first_trade is None:
        return out
    for y in range(START.year, END.year + 1):
        a, b = max(pd.Timestamp(f"{y}-01-01"), START), min(pd.Timestamp(f"{y + 1}-01-01"), END)
        if pd.Timestamp(first_trade) > a + pd.Timedelta(days=45) or (b - a).days < 270:
            continue
        _, s = seg(c, a, b)
        out[y] = float(s[-1]) if len(s) else 0.0
    return out


def day_stats(idx, c, w):
    """Daily table from an hourly curve: close, intraday worst vs previous close."""
    s = pd.DataFrame({"c": np.asarray(c, float), "w": np.asarray(w, float)}, index=idx)
    d = s.groupby(s.index.normalize()).agg(c=("c", "last"), w=("w", "min"))
    prev = d.c.shift(1).fillna(0.0)
    d["day_pnl"] = d.c - prev; d["day_low"] = d.w - prev
    return d


def strat_stats(x, c, w, t):
    """Per-strategy facts at 1% ($10K): dev steadiness, $/month per period, unseen periods."""
    first = str(t.entry_time.min())[:10] if t is not None and len(t) else None
    out = dict(i=x["i"], name=x["name"], symbol=x["symbol"], tf=x["tf"], group=x["group"], mgroup=x["mgroup"],
               src=x["src"], mixes=",".join(x["mixes"]), in24=("24" in x["mixes"]), live_risk=x["live_risk"],
               first_trade=first, offered=x["symbol"] not in NOT_OFFERED)
    if first is None:
        return out
    yr = yearly(c, first)
    dev_years = {y: v for y, v in yr.items() if y <= DEV_END.year}
    out["years_dev"] = len(dev_years); out["pos_years_dev"] = int(sum(v > 0 for v in dev_years.values()))
    out["steady_dev"] = (out["pos_years_dev"] / len(dev_years)) if dev_years else None
    out["yearly"] = {str(k): round(v) for k, v in yr.items()}
    for lab, (a, b) in PERIODS.items():
        a2 = max(pd.Timestamp(a), pd.Timestamp(first))
        if a2 >= pd.Timestamp(b):
            out[f"{lab}_net"] = None; out[f"{lab}_pm"] = None; out[f"{lab}_trades"] = 0; continue
        idx, s = seg(c, a2, b); _, sw = seg(w, a2, b)
        out[f"{lab}_net"] = float(s[-1]); out[f"{lab}_pm"] = float(s[-1]) / months_in(a2, b)
        tt = t[(t.entry_time >= a2) & (t.entry_time < pd.Timestamp(b))]
        out[f"{lab}_trades"] = int(len(tt))
        if lab in ("dev", "unseen3"):
            d = day_stats(idx, s, sw)
            peak = np.maximum.accumulate(np.r_[0.0, s])[1:]
            out[f"{lab}_worst_day"] = float(d.day_low.min()); out[f"{lab}_max_dd"] = float((sw - peak).min())
            out[f"{lab}_months"] = months_in(a2, b)
    return out


# ------------------------------------------------------------------ fast daily account model (selection only)
def fast_account(idx, c, w, acct):
    """Approximate close-all replay on an hourly mix curve: a day whose intraday low vs the previous
    close reaches -halt ends at -(halt+slip). Returns net, lowest balance offset, stop days, per-day series."""
    halt, slip = acct["halt"], acct["slip"]
    c = np.asarray(c, float); w = np.asarray(w, float)
    day = idx.normalize().to_numpy()
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]]); ends = np.r_[starts[1:], len(idx)] - 1
    cprev = np.r_[0.0, c[ends[:-1]]]
    dmin = np.minimum.reduceat(w, starts) - cprev
    res = np.where(dmin <= -halt, -(halt + slip), c[ends] - cprev)
    A = np.r_[0.0, np.cumsum(res)]
    lows = np.maximum(dmin, -(halt + slip))
    low = float((A[:-1] + lows).min())
    di = pd.DatetimeIndex(day[starts])
    return dict(net=float(A[-1]), low=low, halts=int((dmin <= -halt).sum()),
                days=pd.Series(res, index=di), lows=pd.Series(lows, index=di))


def challenges(day_pnl, day_low, floor, target, every=14):
    """Fresh challenge start every `every` days: fail if intraday equity reaches -floor before the
    close reaches +target; pass otherwise when +target is reached; else unfinished."""
    cum = day_pnl.cumsum(); dates = day_pnl.index
    prev = cum.shift(1).fillna(0.0)
    passed = failed = open_ = 0
    for st in pd.date_range(dates[0], dates[-1] - pd.Timedelta(days=30), freq=f"{every}D"):
        k = int(np.searchsorted(dates.values, st.to_datetime64()))
        if k >= len(dates):
            break
        base = float(cum.iloc[k - 1]) if k > 0 else 0.0
        eq = cum.iloc[k:].to_numpy() - base
        lo = (prev.iloc[k:].to_numpy() - base) + day_low.iloc[k:].to_numpy()
        f = np.flatnonzero(lo <= -floor); p = np.flatnonzero(eq >= target)
        f = f[0] if len(f) else None; p = p[0] if len(p) else None
        if f is not None and (p is None or f <= p):
            failed += 1
        elif p is not None:
            passed += 1
        else:
            open_ += 1
    return dict(passed=passed, failed=failed, unfinished=open_)


def period_report(day_pnl, day_low, acct, start, end):
    """Plain-language numbers for one period from daily P&L / daily lows (already account-scaled)."""
    m = (day_pnl.index >= pd.Timestamp(start)) & (day_pnl.index < pd.Timestamp(end))
    dp, dl = day_pnl[m], day_low[m]
    if not len(dp):
        return None
    mon = dp.groupby(dp.index.to_period("M")).sum()
    cum = dp.cumsum()
    ch = challenges(dp, dl, acct["floor"], acct["target"])
    return dict(profit=round(float(dp.sum())), per_month=round(float(dp.sum()) / months_in(start, end)),
                green_months=f"{int((mon > 0).sum())}/{len(mon)}", worst_month=round(float(mon.min())),
                stop_days=int((dl <= -acct["halt"]).sum()),
                lowest_balance=round(acct["start_bal"] + float((cum.shift(1).fillna(0.0) + dl).min())),
                worst_day=round(float(dl.min())), **ch)


# ------------------------------------------------------------------ exact replay of a mix (final numbers)
def mix_sims(entries, acct, start, end, workers=2):
    """entries: dicts with the strategy fields + risk ($10K fraction). Exact sims at the account's scale."""
    jobs = []
    for m in entries:
        r = min(m["risk"] * acct["scale"], RISK_CAP)
        jobs.append((m, r, pd.Timestamp(start), pd.Timestamp(end)))
    t0 = time.time()
    with Pool(workers, maxtasksperchild=40) as pp:
        res = list(pp.imap(C3.run, jobs, chunksize=2))
    print(f"  exact sims {acct['label']}: {len(jobs)} in {time.time() - t0:.0f}s", flush=True)
    return res


def exact_replay(runs, acct):
    """Account-wide close-all replay (the live bot's daily stop) -> daily P&L and daily lows."""
    idx = pd.DatetimeIndex(sorted(set().union(*[set(cv.time) for _, cv, _ in runs])
                                  | set().union(*[set(t.entry_time) | set(t.exit_time) for _, _, t in runs if len(t)])))
    strats = [P.Strat(k, cv, t, idx) for k, cv, t in runs]
    C, W, halts, trades = P.halt_replay(strats, idx, "close_all", halt=acct["halt"], slip=acct["slip"])
    d = day_stats(idx, C, W)
    return d.day_pnl, d.day_low, dict(halts=halts, trades=trades)


def replay_report(entries, acct, start, end, periods, label=""):
    runs = mix_sims(entries, acct, start, end)
    dp, dl, info = exact_replay(runs, acct)
    out = {lab: period_report(dp, dl, acct, a, b) for lab, (a, b) in periods.items()}
    per_strat = {}
    for (k, cv, t) in runs:
        per_strat[k] = {lab: (round(float(t[(t.entry_time >= a) & (t.entry_time < b)].profit.sum())) if len(t) else 0)
                        for lab, (a, b) in periods.items()}
    return dict(label=label, acct=acct["label"], periods=out, per_strategy=per_strat, info=info, day_pnl=dp, day_low=dl)


if __name__ == "__main__":
    pool = build_pool()
    build_cache(pool)
