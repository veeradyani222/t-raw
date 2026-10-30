"""Sweep runner for the round-3 majors group. Pool(2) at most (RAM).

    python research/search3/majors/run.py [batch ...]

Appends one JSON line per scored run to results.jsonl (resumable: already
scored keys are skipped). Scores on the OOS window (PROP_OOS=1, counted from
2024-10-20)."""
import itertools
import json
import os
import sys
import time
from multiprocessing import Pool

os.environ["PROP_OOS"] = "1"
sys.path.insert(0, ".")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results.jsonl")
SYMS = ["EURUSD", "GBPUSD", "USDCHF", "EURGBP", "EURCHF", "GBPCHF"]


def grid(**kw):
    keys = list(kw)
    for vals in itertools.product(*(kw[k] for k in keys)):
        yield dict(zip(keys, vals))


# batch name -> (idea, tfs, param grid list, extra score kwargs)
BATCHES = {
    "asia_bo_h1": ("asia_breakout", ["H1"],
                   list(grid(sl_mode=["mid", "opp"], tp_mode=["rr", "range", "pd"], rr=[1.5, 2.5],
                             max_range=[0.6, 1.0])), {}),
    "asia_bo_m30": ("asia_breakout", ["M30"],
                    list(grid(sl_mode=["mid", "opp"], tp_mode=["rr", "range"], rr=[2.0], max_range=[0.8])), {}),
    "asia_sweep": ("asia_sweep_reversal", ["H1", "M30"],
                   list(grid(pen=[0.02, 0.08], tp_mode=["opp", "rr"], end=[11, 13])), {}),
    "pd_sweep_h1": ("pd_sweep_reversal", ["H1"],
                    list(grid(hours=[(8, 20), (10, 18)], pen=[0.0, 0.1], tp_mode=["mid", "rr", "opp"],
                              max_hold=[12, 24])), {}),
    "pd_sweep_h4": ("pd_sweep_reversal", ["H4"],
                    list(grid(hours=[(0, 23)], pen=[0.0, 0.1], tp_mode=["mid", "rr", "opp"], max_hold=[6])), {}),
    "pw_sweep": ("pw_sweep_reversal", ["H1", "H4"],
                 list(grid(hours=[(0, 23)], pen=[0.0, 0.1], tp_mode=["mid", "rr"])), {}),
    "pd_break": ("pd_break_continuation", ["H1"],
                 list(grid(sl_mode=["level", "bar"], rr=[1.5, 3.0], buf=[0.05, 0.15]))
                 + list(grid(sl_mode=["level", "bar"], tp_mode=["atr"], buf=[0.05, 0.15])), {}),
    "pivot": ("pivot_touch", ["H1"],
              list(grid(lvl=["r1s1", "r2s2"], tp_mode=["piv", "rr"], tol=[0.05, 0.15])), {}),
    "monday_gap": ("monday_gap_fade", ["H1"],
                   list(grid(min_gap=[0.1, 0.2, 0.35], sl_mult=[1.0, 2.0], max_hold=[12, 36])), {}),
    "fix_fade": ("fix_fade", ["H1"],
                 list(grid(fix_bar=[16, 17], thr=[0.25, 0.4], tp_mode=["half", "full", "rr"])), {}),
    "ldn_open_rev": ("london_open_reversal", ["H1"],
                     list(grid(nbars=[1, 2], thr=[0.3, 0.5], tp_mode=["half", "full", "rr"])), {}),
    "trend_day": ("trend_day_continuation", ["H1"],
                  list(grid(hour=[14, 15, 16, 18], k=[0.8, 1.0, 1.3], sl_mode=["mid", "open"])), {}),
    "range_day": ("range_day_fade", ["H1"],
                  list(grid(start=[12, 14], f=[0.5, 0.7], tp_mode=["mid", "opp"])), {}),
    "inside_nr_d1": ("inside_nr_break", ["D1"],
                     list(grid(kind=["inside", "nr7"], sl_mode=["opp", "mid"], rr=[1.5, 3.0]))
                     + list(grid(kind=["inside", "nr7"], sl_mode=["opp", "mid"], trail=[1.5, 3.0], max_hold=[15])), {}),
    "inside_nr_h4": ("inside_nr_break", ["H4"],
                     list(grid(kind=["inside", "nr7"], sl_mode=["opp", "mid"], rr=[2.0], max_hold=[18]))
                     + list(grid(kind=["inside", "nr7"], sl_mode=["opp", "mid"], trail=[2.0], max_hold=[60])), {}),
    "d1_rev": ("d1_reversal", ["D1"],
               list(grid(thr=[1.0, 1.3, 1.6], sl_atr=[0.7, 1.2], hold=[1, 3], use_range=[False, True])), {}),
    "h4_rev": ("d1_reversal", ["H4"],
               list(grid(thr=[1.3, 1.8], sl_atr=[1.0], hold=[3, 6], use_range=[False, True])), {}),
    "round": ("round_number_fade", ["H1"],
              list(grid(step=[0.005, 0.01], rr=[1.0, 2.0], max_hold=[8, 24])), {}),
    "wk_open": ("weekly_open_reversion", ["H1", "H4"],
                list(grid(days=[(2, 3), (3, 4)], thr=[1.2, 1.8, 2.5], sl_atr=[1.0, 1.5])), {}),
    "day_open": ("day_open_reversion", ["H1"],
                 list(grid(start=[12, 14], thr=[0.6, 0.9, 1.2], sl_atr=[0.3, 0.5])), {}),
    "ny_overlap": ("ny_overlap_continuation", ["H1"],
                   list(grid(entry_hour=[15, 16], thr=[0.3, 0.5], sl_mode=["mid", "atr"], exit_hour=[19, 22])), {}),
    "friday": ("friday_week_fade", ["H1"],
               list(grid(hour=[14, 16, 18], thr=[0.8, 1.2, 1.8], tp_frac=[0.5, 1.0])), {}),
    "rollover": ("rollover_dip", ["H1"],
                 [dict(p, spread_mult=sm) for p in grid(sl_atr=[0.3, 0.6], min_drop=[0.0, 0.05]) for sm in (1.0, 3.0)], {}),
}


def key(batch, idea, sym, tf, params):
    return json.dumps([batch, idea, sym, tf, params], sort_keys=True, default=str)


_CACHE = {}


def one(job):
    batch, idea, sym, tf, params = job
    from research.prop import harness as H
    from research.search3.majors import strategies as S
    params = dict(params)
    spread_mult = params.pop("spread_mult", 1.0)
    t0 = time.time()
    try:
        if _CACHE.get("k") != (sym, tf):          # one df per worker (RAM is tight)
            _CACHE.clear(); _CACHE["k"] = (sym, tf); _CACHE["df"] = H.load(sym, tf, split="oos")
        df = _CACHE["df"]
        sigs = S.BUILDERS[idea](df, **params)
        s = H.score(df, sigs, name=f"{batch}:{idea}", spread_mult=spread_mult)
        h = s["headline"]
        row = dict(batch=batch, idea=idea, symbol=sym, tf=tf, params=params, spread_mult=spread_mult,
                   best_risk=s["best_risk"], net=h.get("net"), avg_month=h.get("avg_month"),
                   green=h.get("green_months"), max_dd=h.get("max_dd"), worst_day=h.get("worst_day"),
                   trades=h.get("trades"), win=h.get("win_rate"), chal=h.get("challenge_pass_rate"),
                   months=h.get("months"), net_025=s["by_risk"]["0.0025"].get("net"),
                   secs=round(time.time() - t0, 1), key=key(batch, idea, sym, tf, params | ({"spread_mult": spread_mult} if spread_mult != 1.0 else {})))
    except Exception as e:  # keep the sweep alive, record the failure
        row = dict(batch=batch, idea=idea, symbol=sym, tf=tf, params=params, error=repr(e),
                   key=key(batch, idea, sym, tf, params | ({"spread_mult": spread_mult} if spread_mult != 1.0 else {})))
    return row


def main():
    names = sys.argv[1:] or list(BATCHES)
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            try:
                r = json.loads(line)
                if "error" not in r:
                    done.add(r["key"])
            except Exception:
                pass
    jobs = []
    for b in names:
        idea, tfs, grid_, _ = BATCHES[b]
        for sym in SYMS:
            for tf in tfs:
                for p in grid_:
                    k = key(b, idea, sym, tf, p)
                    if k not in done:
                        jobs.append((b, idea, sym, tf, p))
    print(f"{len(jobs)} jobs to run ({len(done)} already done)", flush=True)
    t0 = time.time()
    with Pool(2) as pool, open(OUT, "a") as f:
        for n, row in enumerate(pool.imap_unordered(one, jobs, chunksize=2), 1):
            f.write(json.dumps(row, default=str) + "\n"); f.flush()
            if "error" in row:
                print("ERR", row["batch"], row["symbol"], row["tf"], row["params"], row["error"], flush=True)
            elif n % 25 == 0 or row.get("avg_month", 0) > 60:
                print(f"[{n}/{len(jobs)} {time.time()-t0:.0f}s] {row['batch']} {row['symbol']} {row['tf']} "
                      f"{row['params']} risk={row['best_risk']} avg/mo={row['avg_month']:.0f} "
                      f"dd={row['max_dd']:.0f} wd={row['worst_day']:.0f} n={row['trades']}", flush=True)
    print("done", time.time() - t0)


if __name__ == "__main__":
    main()
