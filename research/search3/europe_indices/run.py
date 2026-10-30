"""Scored sweep runner. Usage:
    python research/search3/europe_indices/run.py <batch|all> [workers=2]
Appends one JSON line per run to results.jsonl (resumable: done keys are skipped)."""
import sys, json, itertools, functools, traceback
sys.path.insert(0, ".")
from pathlib import Path
from multiprocessing import Pool
from research.search3.europe_indices.common import *
from research.search3.europe_indices import strategies as S

HERE = Path(__file__).resolve().parent
OUT = HERE / "results.jsonl"
SYMS = ["UK100", "FRA40", "IT40", "DE40", "ESP35"]
STEP = {"DE40": 100.0, "FRA40": 50.0, "IT40": 250.0, "UK100": 50.0, "ESP35": 100.0}


def grid(**kw):
    keys = list(kw)
    for vals in itertools.product(*[kw[k] for k in keys]):
        yield dict(zip(keys, vals))


def tag(builder, p):
    bits = [builder] + [f"{k}={v}" for k, v in p.items()]
    return "_".join(bits).replace(" ", "").replace("'", "").replace("(", "").replace(")", "").replace(",", ".")


def batches():
    B = {}
    # 1 gap
    g = []
    for p in grid(mode=["fade"], gmin=[0.2, 0.4], gmax=[1.0, 2.0], sl_mult=[1.0, 1.5], tp=["fill", "r"]):
        if p["tp"] == "r":
            p["tp_r"] = 1.5
        g.append(p)
    g += list(grid(mode=["cont"], gmin=[0.3, 0.5], gmax=[2.0], tp_r=[1.5, 2.5]))
    g += list(grid(mode=["fade"], gmin=[0.3], gmax=[1.5], entry_hm=[10.5, 11.0]))
    g += list(grid(mode=["fade"], gmin=[0.3], gmax=[1.5], trend=["with", "against"]))
    g += list(grid(mode=["fade"], gmin=[0.3], gmax=[1.5], sides=["long", "short"]))
    B["gap"] = [("gap", "M30", s, p) for s in SYMS for p in g] + \
               [("gap", "H1", s, p) for s in SYMS for p in grid(mode=["fade", "cont"], gmin=[0.3], gmax=[1.5], sl_mult=[1.0, 1.5])]
    # 2 us open fade
    u = list(grid(k=[0.8, 1.2], tp=["retrace", "r"], sl_mult=[1.0]))
    u += list(grid(k=[1.0], mode=["cont"], tp_r=[1.0, 2.0]))
    u += list(grid(k=[1.0], trend=["with", "against"]))
    u += list(grid(k=[1.0], sides=["long", "short"]))
    B["usopen"] = [("us_open_fade", "M30", s, p) for s in SYMS for p in u] + \
                  [("us_open_fade", "H1", s, p) for s in SYMS for p in grid(k=[0.8, 1.2], bar_hm=[16.0], tp=["retrace", "r"])]
    # 3 close fade
    cf = list(grid(k=[0.2, 0.4], mode=["fade", "follow"], entry_hm=[17.5], hold=[1]))
    cf += list(grid(k=[0.2, 0.4], mode=["fade", "follow"], entry_hm=[17.0], hold=[2]))
    cf += list(grid(k=[0.3], mode=["fade"], sides=["long", "short"]))
    cf += list(grid(k=[0.3], mode=["fade"], from_hm=[16.5], entry_hm=[17.5]))
    B["close"] = [("close_fade", "M30", s, p) for s in SYMS for p in cf]
    # 4 overnight
    ov = list(grid(side=["long"], cond=[None, "down_day", "up_day", "down_vs_pdc"], sl_datr=[0.75, 1.5]))
    ov += list(grid(side=["short"], cond=[None, "up_day"], sl_datr=[1.0]))
    ov += list(grid(side=["long"], cond=[None], sl_datr=[1.0], skip_wd=[()], entry_hm=[18.0, 19.0]))
    ov += list(grid(side=["long"], cond=[None], sl_datr=[1.0], trend=["with"]))
    B["overnight"] = [("overnight", "M30", s, p) for s in SYMS for p in ov]
    # 5 orb
    ob = list(grid(re=[10.5, 11.0], sl=["far", "mid"], tp_r=[2.0, None], trend=[None, "with"]))
    ob += list(grid(re=[10.5], te=[14.0, 16.0], sl=["far"], tp_r=[2.0], trend=["with"]))
    ob += list(grid(re=[10.5], sl=["far"], tp_r=[2.0], trend=["with"], exit_hour=[22]))
    B["orb"] = [("orb", "M30", s, p) for s in SYMS for p in ob]
    # 6 or_fail
    of = list(grid(re=[10.5, 11.0], tp=["far", "mid", "r"], trend=[None, "with"]))
    of += list(grid(re=[10.5], tp=["far"], te=[13.0, 14.0]))
    of += list(grid(re=[10.5], tp=["far"], sides=["long", "short"]))
    B["orfail"] = [("or_fail", "M30", s, p) for s in SYMS for p in of]
    # 7 pdhl
    pd_ = list(grid(mode=["reject"], tp=["mid", "far"], sl_atr=[1.0, 2.0]))
    pd_ += list(grid(mode=["break"], tp_r=[1.5, None], sl_atr=[1.0, 2.0]))
    pd_ += list(grid(mode=["reject", "break"], trend=["with"]))
    pd_ += list(grid(mode=["reject"], ts=[16.0], te=[18.0], tp=["mid"]))
    B["pdhl"] = [("pdhl", "M30", s, p) for s in SYMS for p in pd_] + \
                [("pdhl", "H1", s, p) for s in SYMS for p in grid(mode=["reject", "break"], sl_atr=[1.0])]
    # 8 round numbers
    rd = []
    for s in SYMS:
        st = STEP[s]
        for p in grid(sl_frac=[0.5], tp_frac=[0.5, 1.0], min_body=[0.0, 0.3]):
            rd.append(("round", "M30", s, dict(step=st, **p)))
        rd.append(("round", "M30", s, dict(step=st, trend="with")))
        for p in grid(touch_atr=[0.1, 0.25], tp=["step", "r"]):
            rd.append(("round_fade", "M30", s, dict(step=st, **p)))
        rd.append(("round_fade", "M30", s, dict(step=st, trend="with")))
    B["round"] = rd
    # 9 late momentum + time windows
    lm = list(grid(bar_hm=[19.0, 20.0], k=[0.5, 0.8], mode=["follow", "fade"]))
    B["late"] = [("late_momentum", "H1", s, p) for s in SYMS for p in lm]
    tw = [dict(entry_hm=19.0, exit_hour=22, side="long"), dict(entry_hm=18.5, exit_hour=22, side="long"),
          dict(entry_hm=19.0, exit_hour=22, side="long", cond="session_up"),
          dict(entry_hm=19.0, exit_hour=22, side="long", cond="session_down"),
          dict(entry_hm=19.0, exit_hour=22, side="long", trend="with"),
          dict(entry_hm=10.0, exit_hour=18, side="long"), dict(entry_hm=10.0, exit_hour=18, side="long", wds=(0,)),
          dict(entry_hm=10.0, exit_hour=18, side="short", wds=(4,)),
          dict(entry_hm=12.0, exit_hour=16, side="long"), dict(entry_hm=16.0, exit_hour=18, side="long"),
          dict(entry_hm=19.0, exit_hour=22, side="long", sl_datr=0.3)]
    B["window"] = [("time_window", "M30", s, p) for s in SYMS for p in tw]
    # 10 lunch
    lb = list(grid(sl=["far", "mid"], tp_r=[1.5, None], trend=[None, "with"]))
    B["lunch"] = [("lunch_break", "M30", s, p) for s in SYMS for p in lb]
    # 11 pullback
    pb = list(grid(rsi_buy=[20, 30], tp_r=[2.0, None], sides=["long", "both"]))
    for p in pb:
        p["rsi_sell"] = 100 - p["rsi_buy"]
        if p["tp_r"] is None:
            p["trail_atr"] = 3.0
    B["pullback"] = [("pullback", tf, s, p) for s in SYMS for tf in ("H1", "H4") for p in pb]
    # 12 D1
    dm = list(grid(n_down=[2, 3], ma=[100, 200], side=["long"]))
    dm += [dict(n_down=0, rsi2_max=10, ma=200), dict(n_down=0, rsi2_max=10, ma=200, use_trend=False),
           dict(n_down=3, ma=200, side="short"), dict(n_down=2, ma=200, exit="hold", max_hold=3)]
    bd = list(grid(k=[1.5, 2.0], mode=["fade", "follow"]))
    B["d1"] = [("d1_meanrev", "D1", s, p) for s in SYMS for p in dm] + [("big_day", "D1", s, p) for s in SYMS for p in bd]
    # 13 prev week
    pw = list(grid(sl_atr=[1.5, 2.5], trail_atr=[3.0, 6.0], trend=[None, "with"]))
    pw += list(grid(sl_atr=[1.5], trail_atr=[3.0], sides=["long", "short"]))
    pw += list(grid(sl_atr=[1.5], trail_atr=[3.0], friday_flat=[False]))
    B["prevweek"] = [("prev_week", tf, s, p) for s in SYMS for tf in ("M30", "H1") for p in pw]
    # 14 calendar
    cal = [dict(kind="tom", tom_days=(-1, 0, 1, 2), hold_days=1), dict(kind="tom", tom_days=(-1, 0), hold_days=2),
           dict(kind="tom", tom_days=(0, 1, 2, 3), hold_days=1), dict(kind="tom", tom_days=(-1, 0, 1, 2), hold_days=1, sl_datr=1.5),
           dict(kind="tom", tom_days=(-1,), hold_days=4), dict(kind="tom", tom_days=(-1, 0, 1, 2), hold_days=1, entry_hm=18.0),
           dict(kind="weekday", wd=0, side="long"), dict(kind="weekday", wd=4, side="short"), dict(kind="weekday", wd=3, side="short"),
           dict(kind="weekday", wd=0, side="long", entry_hm=18.0, exit_hour=10)]
    B["calendar"] = [("calendar", "M30", s, p) for s in SYMS for p in cal]
    # 15 compression
    cb = list(grid(kind=["nr4", "nr7", "inside"], sl=["mid", "far"]))
    cb += list(grid(kind=["nr7"], sl=["mid"], trend=["with"], tp_r=[2.0, None]))
    B["compress"] = [("compression_break", "M30", s, p) for s in SYMS for p in cb]
    # 16 fh retest
    fr = list(grid(fh_end=[11.0, 11.5], mm=[1.5, 2.5], trend=[None, "with"]))
    fr += list(grid(fh_end=[11.0], mm=[1.5], sl=["mid"]))
    B["fhretest"] = [("fh_retest", "M30", s, p) for s in SYMS for p in fr]
    # 17 donchian
    dc = list(grid(n_ch=[20, 40, 80], trail_atr=[3.0, 5.0], trend=[None, "with"]))
    B["donchian"] = [("donchian", "H4", s, p) for s in SYMS for p in dc] + \
                    [("donchian", "D1", s, p) for s in SYMS for p in grid(n_ch=[20, 55], trail_atr=[3.0])]
    # 18 kagels 09:15 candle (M30 proxy on all; true M15 on DE40 which has m15 data)
    kg = list(grid(bar_hm=[10.0], bar_len=[0.5], tp_r=[1.5, None], sl=["far", "mid"], te=[14.0]))
    kg += list(grid(bar_hm=[10.0], bar_len=[0.5], tp_r=[None], sl=["far"], sides=["long", "short"], te=[14.0]))
    kg += list(grid(bar_hm=[10.0], bar_len=[0.5], tp_r=[None], sl=["far"], trend=["with"], te=[14.0, 12.0]))
    B["kagels"] = [("kagels_915", "M30", s, p) for s in SYMS for p in kg]
    k15 = list(grid(tp_r=[1.5, None], sl=["far", "mid"], te=[14.0]))
    k15 += [dict(tp_pts=20, sl="far"), dict(tp_pts=40, sl="far"), dict(tp_r=None, sl="far", sides="long"),
            dict(tp_r=None, sl="far", trend="with"), dict(tp_r=None, sl="far", te=12.0), dict(tp_r=None, sl="far", wds=(1, 2, 3))]
    B["kagels"] += [("kagels_915", "M15", "DE40", p) for p in k15]
    # 19 first-hour multiplier breakout
    fm = list(grid(mult=[0.25, 0.5, 1.0], sl=["opp", "ref"], tp_r=[None, 2.0]))
    fm += list(grid(mult=[0.5], sl=["opp"], trend=["with"], te=[14.0, 16.0]))
    fm += list(grid(mult=[0.5], sl=["opp"], sides=["long", "short"]))
    B["fhmult"] = [("fh_mult", "M30", s, p) for s in SYMS for p in fm]
    # 20 close-to-open (STOXX overnight effect)
    co = list(grid(side=["long"], cond=[None, "down_cash", "up_cash", "below_pdc"], sl_datr=[0.75, 1.5]))
    co += [dict(side="long", wds=(0, 1, 2, 3, 4)), dict(side="short", cond="up_cash"), dict(side="long", exit_hm=11.0),
           dict(side="long", entry_hm=17.5, exit_hm=10.0)]
    B["c2o"] = [("close_to_open", "M30", s, p) for s in SYMS for p in co]
    # 21 intraday momentum (first half hour -> last half hour)
    im = list(grid(entry_hm=[17.5], exit_hour=[18], sl_datr=[0.3, 0.75], agree_prev=[False, True], mode=["follow", "fade"]))
    im += list(grid(entry_hm=[17.5], exit_hour=[18], sl_datr=[0.5], min_move_datr=[0.15, 0.3]))
    im += list(grid(entry_hm=[17.0], exit_hour=[18], sl_datr=[0.5], agree_prev=[False, True]))
    im += list(grid(entry_hm=[22.0], exit_hour=[22], sl_datr=[0.5], agree_prev=[False, True]))
    im += list(grid(entry_hm=[17.5], exit_hour=[18], sl_datr=[0.5], sides=["long", "short"]))
    B["imom"] = [("intraday_mom", "M30", s, p) for s in SYMS for p in im]
    return B


@functools.lru_cache(maxsize=4)
def _df(sym, tf):
    return load(sym, tf)


def one(job):
    builder, tf, sym, params = job
    name = tag(builder, params)
    try:
        df = _df(sym, tf)
        sigs = S.BUILDERS[builder](df, **params)
        r = H.score(df, sigs, name=name)
        h = r["headline"]
        rec = dict(name=name, builder=builder, symbol=sym, tf=tf, params=params, best_risk=r["best_risk"],
                   avg_month=h.get("avg_month", 0.0), net=h.get("net", 0.0), max_dd=h.get("max_dd", 0.0),
                   worst_day=h.get("worst_day", 0.0), trades=h.get("trades", 0),
                   green_months=h.get("green_months", 0.0), win_rate=h.get("win_rate", 0.0),
                   chal=h.get("challenge_pass_rate", 0.0), months=h.get("months", 0),
                   monthly=h.get("monthly", {}))
        return rec
    except Exception as e:
        return dict(name=name, builder=builder, symbol=sym, tf=tf, params=params, error=f"{e!r}",
                    tb=traceback.format_exc()[-500:])


def key(rec):
    return (rec["name"], rec["symbol"], rec["tf"])


def done_keys():
    if not OUT.exists():
        return set()
    out = set()
    for line in OUT.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if "error" not in r:
                out.add(key(r))
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    B = batches()
    jobs = []
    names = list(B) if which == "all" else which.split(",")
    for nm in names:
        jobs += B[nm]
    done = done_keys()
    jobs = [j for j in jobs if (tag(j[0], j[3]), j[2], j[1]) not in done]
    # group by (sym, tf) so each worker's cache is warm
    jobs.sort(key=lambda j: (j[2], j[1]))
    print(f"{len(jobs)} jobs to run ({which})", flush=True)
    with OUT.open("a") as f, Pool(workers) as pool:
        for k, rec in enumerate(pool.imap(one, jobs, chunksize=4)):
            f.write(json.dumps(rec, default=str) + "\n"); f.flush()
            if "error" in rec:
                print("ERR", rec["name"], rec["symbol"], rec["tf"], rec["error"], flush=True)
            elif k % 20 == 0:
                print(k, rec["name"], rec["symbol"], rec["tf"], rec["best_risk"], round(rec["avg_month"]), flush=True)


if __name__ == "__main__":
    main()
