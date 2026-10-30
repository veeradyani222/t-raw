"""Sweep runner. PYTHONPATH=. python research/search3/us_indices/run.py [batch|all] [workers]
Writes research/search3/us_indices/results.jsonl (one line per scored run, with the
look-ahead check result)."""
import os, sys, json, time, random, traceback
os.environ["PROP_OOS"] = "1"
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from research.prop import harness as H
from research.search3.us_indices import strategies as S

OUT = Path(__file__).with_name("results.jsonl")
SYMS = [s for s in ("US30", "US500", "USTEC", "US2000") if (H.DATA / f"{s.lower()}-h1.csv").exists()]
_cache = {}


def load(sym, tf):
    k = (sym, tf)
    if k not in _cache:
        _cache.clear()
        _cache[k] = H.load(sym, tf, split="oos")
    return _cache[k]


def _same(a, b):
    if a is None or b is None:
        return a is b
    return (a.side == b.side and np.isclose(a.sl, b.sl) and
            ((a.tp is None and b.tp is None) or (a.tp is not None and b.tp is not None and np.isclose(a.tp, b.tp))) and
            a.max_hold == b.max_hold and a.exit_hour == b.exit_hour)


def lookahead_check(build, df, params, full, seed=0):
    rng = random.Random(seed)
    n = len(df)
    for _ in range(5):
        k = rng.randint(n // 3, n - 2)
        sub = df.iloc[:k].reset_index(drop=True)
        sub.attrs.update(df.attrs)
        part = build(sub, **params)
        for i in range(k):
            if not _same(full[i], part[i]):
                return False, f"k={k} i={i} full={full[i]} part={part[i]}"
    return True, ""


def one(job):
    name, bname, sym, tf, params = job
    try:
        df = load(sym, tf)
        build = S.BUILDERS[bname]
        t0 = time.time()
        sigs = build(df, **params)
        ok, why = lookahead_check(build, df, params, sigs)
        s = H.score(df, sigs, name=name)
        h = s["headline"]
        row = dict(name=name, builder=bname, symbol=sym, tf=tf, params=params, best_risk=s["best_risk"],
                   causal_ok=ok, causal_why=why, n_signals=int(sum(x is not None for x in sigs)),
                   secs=round(time.time() - t0, 1),
                   **{k: h.get(k) for k in ("trades", "win_rate", "net", "avg_month", "green_months", "worst_month",
                                             "max_dd", "worst_day", "challenge_pass_rate", "months")})
        row["by_risk"] = {r: dict(avg=round(m.get("avg_month", 0), 1), dd=round(m.get("max_dd", 0)), wd=round(m.get("worst_day", 0)))
                          for r, m in s["by_risk"].items()}
        if s["best_risk"] is not None:
            row["monthly"] = {k: v for k, v in s["by_risk"].items()} and None
            tr = s["trades_at_best"]
            if tr is not None and len(tr):
                row["reasons"] = tr["reason"].value_counts().to_dict()
        return row
    except Exception as e:
        return dict(name=name, builder=bname, symbol=sym, tf=tf, params=params, error=traceback.format_exc()[-800:])


def jobs(batch):
    J = []
    def add(bname, tf, syms=None, **params):
        for sym in (syms or SYMS):
            tag = "_".join(f"{k}{v}" for k, v in params.items()).replace(" ", "").replace("[", "").replace("]", "").replace(",", "-")
            J.append((f"{bname}:{tag}", bname, sym, tf, params))
    B = batch
    if B in ("all", "d1"):
        for db in (1, 2, 5):
            for da in (2, 3):
                add("tom", "D1", days_before=db, days_after=da, sl_atr=1.5)
        add("tom", "D1", days_before=1, days_after=3, sl_atr=1.5, trend="with")
        add("tom", "D1", days_before=5, days_after=3, sl_atr=2.5)
        add("tom", "D1", days_before=2, days_after=2, sl_atr=1.0)
        for mode in ("short_week", "long_after", "long_week"):
            add("opex", "D1", mode=mode, sl_atr=1.5)
        add("opex", "D1", mode="long_after", sl_atr=1.5, trend="with")
        for n in (10, 20):
            for mode in ("long", "both"):
                add("turtle_soup", "D1", n=n, mode=mode, hold=5, exit_rule="hold")
                add("turtle_soup", "D1", n=n, mode=mode, hold=10, exit_rule="pdh")
        add("turtle_soup", "D1", n=20, mode="long", hold=5, exit_rule="hold", tp_r=2.0)
        add("turtle_soup", "D1", n=20, mode="long", hold=3, exit_rule="hold", sl_pad=0.5)
        for th in (5, 10):
            for ex in (5, 10):
                add("rsi2", "D1", thresh=th, exit_sma=ex)
        add("rsi2", "D1", thresh=10, exit_sma=5, side="short")
        add("rsi2", "D1", thresh=10, exit_sma=5, sl_atr=3.0)
        for k in (2, 3):
            for ex in ("hold", "pdh"):
                for tr in (True, False):
                    add("down_streak", "D1", k=k, exit_rule=ex, trend_req=tr)
        add("down_streak", "D1", k=3, exit_rule="hold", hold=10, trend_req=True)
        add("down_streak", "D1", k=3, exit_rule="hold", hold=5, trend_req=True, tp_r=1.5)
        for dow in (4, 0, 2):
            add("weekday", "D1", enter_dow=dow, hold=1)
        add("weekday", "D1", enter_dow=3, hold=1, side="short")
        add("weekday", "D1", enter_dow=4, hold=1, trend="with")
        add("weekday", "D1", enter_dow=4, hold=1, sl_atr=1.0)
        for drop in (1.5, 2.5):
            for ex in ("hold", "pdh"):
                add("capitulation", "D1", drop_atr=drop, exit_rule=ex)
        add("capitulation", "D1", drop_atr=1.5, exit_rule="hold", vol_mult=1.0)
    if B in ("all", "h1"):
        for eh in (16, 20):
            add("fomc", "H1", mode="pre_drift", entry_hour=eh, sl_atr=1.0)
        add("fomc", "H1", mode="pre_drift", entry_hour=20, sl_atr=2.0)
        add("fomc", "H1", mode="post_mom", sl_atr=0.7)
        add("fomc", "H1", mode="post_fade", sl_atr=0.7)
        for (a, b) in ((15, 16), (16, 17), (17, 18), (18, 19), (19, 20), (20, 21), (21, 22), (19, 22), (16, 22),
                       (5, 6), (9, 10), (9, 12), (12, 13), (18, 21), (16, 18), (1, 4)):
            add("hour_window", "H1", entry_hour=a, exit_hour=b, side="long", sl_atr=0.6)
        for (a, b) in ((16, 17), (17, 18), (18, 19), (20, 21), (21, 22), (14, 15)):
            add("hour_window", "H1", entry_hour=a, exit_hour=b, side="short", sl_atr=0.6)
        for cond in ("day_down", "below_pdc", "day_up"):
            add("hour_window", "H1", entry_hour=19, exit_hour=21, side="long", sl_atr=0.6, cond=cond)
            add("hour_window", "H1", entry_hour=19, exit_hour=22, side="long", sl_atr=1.0, cond=cond)
        add("hour_window", "H1", entry_hour=19, exit_hour=21, side="long", sl_atr=1.0, trend="with")
        add("hour_window", "H1", entry_hour=19, exit_hour=21, side="long", sl_atr=0.3)
        add("hour_window", "H1", entry_hour=19, exit_hour=21, side="long", sl_atr=0.6, dow=[0, 1, 2])
        add("hour_window", "H1", entry_hour=16, exit_hour=17, side="long", sl_atr=0.6, cond="below_pdc")
        add("hour_window", "H1", entry_hour=16, exit_hour=17, side="long", sl_atr=0.6, trend="with")
        for tf in ("H1", "H4"):
            for sides in ("both", "long"):
                add("prev_week", tf, mode="break", stop="mid", sides=sides)
                add("prev_week", tf, mode="break", stop="atr", sides=sides)
                add("prev_week", tf, mode="fade", sides=sides)
            add("prev_week", tf, mode="break", stop="mid", sides="long", trend="with")
            add("prev_week", tf, mode="break", stop="atr", sides="both", tp_r=2.0)
            for sides in ("long", "both"):
                add("h4_pullback", tf, sides=sides, trail=False, tp_r=2.0)
                add("h4_pullback", tf, sides=sides, trail=True)
            add("h4_pullback", tf, sides="long", trail=False, tp_r=3.0, sl_atr=2.0)
            add("h4_pullback", tf, sides="long", fast=10, slow=30, trail=False, tp_r=2.0)
        for tp in (1.5, None):
            for tr in (None, "with"):
                add("asia_break", "H1", tp_r=tp, trend=tr)
        add("asia_break", "H1", tp_r=1.0, exit_hour=12)
        add("overnight", "H1", sl_atr=0.8)
        add("overnight", "H1", sl_atr=1.5, trend="with")
        add("pdl_sweep", "H1", tp="pd_mid", sides="long", sl_pad=0.1)
        add("pdl_sweep", "H1", tp="pd_high", sides="long", sl_pad=0.1)
        add("pdl_sweep", "H1", tp="pd_mid", sides="both", sl_pad=0.1)
    if B in ("all", "m30"):
        for sl in (0.8, 1.5):
            for after in ("any", "down"):
                for tr in (None, "with"):
                    add("overnight", "M30", sl_atr=sl, after=after, trend=tr)
        add("overnight", "M30", sl_atr=0.8, dow=[0, 1, 2, 3])
        add("overnight", "M30", sl_atr=0.8, dow=[4])
        add("overnight", "M30", sl_atr=0.8, after="up")
        add("overnight", "M30", sl_atr=0.5, tp_r=1.0)
        for ob in (1, 2):
            for rv in (None, 1.5):
                for st in ("mid", "far"):
                    for tp in (2.0, None):
                        add("orb", "M30", or_bars=ob, rvol_min=rv, stop=st, tp_r=tp)
        add("orb", "M30", or_bars=1, rvol_min=None, stop="far", tp_r=None, trend="with")
        add("orb", "M30", or_bars=2, rvol_min=None, stop="far", tp_r=None, trend="with")
        add("orb", "M30", or_bars=1, rvol_min=None, stop="far", tp_r=None, sides="long")
        add("orb", "M30", or_bars=1, rvol_min=1.5, stop="far", tp_r=3.0)
        add("orb", "M30", or_bars=1, rvol_min=None, stop="far", tp_r=None, last_entry_hm=1730)
        add("orb", "M30", or_bars=2, rvol_min=None, stop="mid", tp_r=1.0)
        for tp in ("pd_mid", "pd_high", "pd_close"):
            for sides in ("long", "both"):
                for tr in (None, "with"):
                    add("pdl_sweep", "M30", tp=tp, sides=sides, sl_pad=0.1, trend=tr)
        add("pdl_sweep", "M30", tp="pd_mid", sides="long", sl_pad=0.25)
        add("pdl_sweep", "M30", tp="pd_high", sides="long", sl_pad=0.25)
        add("pdl_sweep", "M30", tp=None, sides="long", sl_pad=0.1)
        add("pdl_sweep", "M30", tp="pd_mid", sides="long", sl_pad=0.1, end_hm=1800)
        add("pdl_sweep", "M30", tp="pd_mid", sides="short", sl_pad=0.1)
        for mode in ("nr7", "inside"):
            for st in ("far", "mid"):
                for tp in (2.0, None):
                    add("nr_break", "M30", mode=mode, stop=st, tp_r=tp)
        add("nr_break", "M30", mode="nr7", stop="far", tp_r=None, trend="with")
        add("nr_break", "M30", mode="inside", stop="far", tp_r=None, trend="with")
        for st in ("big", "small"):
            for mode in ("bounce", "break"):
                for tp in (1.5, None):
                    add("round", "M30", step=st, mode=mode, tp_r=tp)
        add("round", "M30", step="big", mode="bounce", tp_r=1.5, trend="with")
        add("round", "M30", step="big", mode="bounce", tp_r=2.5, sl_atr=0.3)
        for th in (0.2, 0.4):
            for mode in ("mom", "fade"):
                add("first_last", "M30", thresh_atr=th, mode=mode)
        add("first_last", "M30", thresh_atr=0.3, mode="mom", entry_hm=2130)
        for wh in ("inside", "outside"):
            for mode in ("fade", "cont"):
                for g in (0.2, 0.4):
                    add("gap_struct", "M30", where=wh, mode=mode, gmin=g)
        add("gap_struct", "M30", where="inside", mode="fade", gmin=0.2, tp="pd_mid")
        add("gap_struct", "M30", where="outside", mode="cont", gmin=0.3, sl_atr=0.8)
        for mode in ("cont", "fade"):
            for th in (0.3, 0.5):
                add("first_hour", "M30", mode=mode, thresh_atr=th)
        add("first_hour", "M30", mode="cont", thresh_atr=0.3, trend="with")
        add("first_hour", "M30", mode="cont", thresh_atr=0.3, tp_r=2.0)
        add("fomc", "M30", mode="pre_drift", entry_hour=20, sl_atr=1.0)
        add("fomc", "M30", mode="post_mom", sl_atr=0.7)
        add("fomc", "M30", mode="post_fade", sl_atr=0.7)
    if B in ("all", "new"):
        for lo in (0.1, 0.2, 0.3):
            for hi in (0.7, 0.8):
                add("ibs", "D1", lo=lo, hi=hi)
        add("ibs", "D1", lo=0.2, hi=0.8, trend_req=False)
        add("ibs", "D1", lo=0.2, hi=0.8, sl_atr=1.5, max_hold=5)
        add("ibs", "D1", lo=0.15, hi=0.9, sma_trend=100)
        for n in (5, 7, 10):
            add("double7s", "D1", n=n)
        add("double7s", "D1", n=7, sl_atr=1.5)
        add("double7s", "D1", n=7, max_hold=8)
        for n in (6, 8, 12):
            for ex in ("nhigh", "hold"):
                add("h4_dip", "H4", n=n, exit_rule=ex)
        add("h4_dip", "H4", n=8, exit_rule="hold", tp_r=1.5, max_hold=12)
        add("h4_dip", "H4", n=8, sl_atr=1.0, daily_sma=100)
        add("h4_dip", "H1", n=12, exit_rule="nhigh")
        add("h4_dip", "H1", n=24, exit_rule="nhigh", max_hold=48)
        for hm in (1900, 2000, 2100):
            for th in (0.3, 0.5):
                add("late_dip", "M30", entry_hm=hm, thresh_atr=th, mode="dip")
        add("late_dip", "M30", entry_hm=2000, thresh_atr=0.4, mode="rip")
        add("late_dip", "M30", entry_hm=2000, thresh_atr=0.4, mode="dip", trend="with")
        add("late_dip", "M30", entry_hm=2000, thresh_atr=0.4, mode="dip", sl_atr=0.3)
        add("late_dip", "H1", entry_hm=2000, thresh_atr=0.4, mode="dip")
        for sides in ("long", "both"):
            for st in ("mid", "atr", "level"):
                for tp in (None, 2.0):
                    add("pdh_break", "M30", sides=sides, stop=st, tp_r=tp)
        add("pdh_break", "M30", sides="long", stop="mid", trend="with")
        add("pdh_break", "M30", sides="long", stop="mid", min_dist=0.1)
        add("pdh_break", "M30", sides="long", stop="mid", end_hm=1800)
        add("pdh_break", "H1", sides="long", stop="mid")
        add("pdh_break", "H1", sides="both", stop="atr", tp_r=2.0)
        for n in (20, 50):
            for tr in (2.0, 3.0):
                add("d1_breakout", "D1", n=n, trail_atr=tr)
        add("d1_breakout", "D1", n=20, trail_atr=3.0, sides="both")
        add("d1_breakout", "D1", n=20, trail_atr=3.0, squeeze=0.9)
        add("d1_breakout", "D1", n=10, trail_atr=2.0, squeeze=0.8)
    return J


if __name__ == "__main__":
    batch = sys.argv[1] if len(sys.argv) > 1 else "all"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    J = jobs(batch)
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                r = json.loads(line); done.add((r["name"], r["symbol"], r["tf"]))
            except Exception:
                pass
    J = [j for j in J if (j[0], j[2], j[3]) not in done]
    # group by (sym, tf) so the per-worker cache hits
    J.sort(key=lambda j: (j[2], j[3]))
    print(f"{len(J)} jobs ({batch}), {workers} workers", flush=True)
    t0 = time.time()
    with Pool(workers) as pool, OUT.open("a") as f:
        for k, row in enumerate(pool.imap_unordered(one, J, chunksize=4)):
            f.write(json.dumps(row, default=str) + "\n"); f.flush()
            if "error" in row:
                print("ERR", row["name"], row["symbol"], row["tf"], row["error"][-300:], flush=True)
            else:
                br = f"{row['best_risk']*100:.2f}%" if row["best_risk"] else "none"
                print(f"[{k+1}/{len(J)} {time.time()-t0:5.0f}s] {row['name']:<48} {row['symbol']:<6}{row['tf']:<4} "
                      f"risk {br:<6} avg/mo {row['avg_month'] or 0:7.0f} dd {row['max_dd'] or 0:6.0f} wd {row['worst_day'] or 0:6.0f} "
                      f"tr {row['trades']:4d} causal {row['causal_ok']}", flush=True)
