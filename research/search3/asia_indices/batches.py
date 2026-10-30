"""Job lists for run.py. A job = (name, build_fn, symbol, tf, params).
Session hours are on the asia clock (UTC+2, DST-free; AUS200 auto-shifted so Sydney = 02:00)."""
from __future__ import annotations
import itertools

SYMS = ["JPN225", "HK50", "CHINA50", "AUS200"]
# cash session on the asia clock: (open, close, lunch)   close = exit bar hour
SESS = {
    "JPN225": dict(M30=(2.0, 8.5, 4.5), H1=(2.0, 8.0, 4.0)),
    "HK50": dict(M30=(3.5, 10.0, 6.0), H1=(3.0, 10.0, 6.0)),
    "CHINA50": dict(M30=(3.5, 9.0, 5.5), H1=(3.0, 9.0, 5.0)),
    "AUS200": dict(M30=(2.0, 8.0, 5.0), H1=(2.0, 8.0, 5.0)),
}
ROUND = {"JPN225": (500, 1000), "HK50": (250, 500), "CHINA50": (100, 250), "AUS200": (50, 100)}


def _j(fn, sym, tf, **p):
    return (fn.replace("build_", ""), fn, sym, tf, p)


def grid(**kw):
    keys = list(kw)
    for vals in itertools.product(*kw.values()):
        yield dict(zip(keys, vals))


def orb():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            o, c, _ = SESS[sym][tf]
            for p in grid(n_bars=(1, 2), tp_r=(0, 1.5), sl_mode=("opp", "mid")):
                out.append(_j("build_orb", sym, tf, open_h=o, close_h=c, **p))
            if sym == "HK50" and tf == "H1":
                for p in grid(n_bars=(1,), tp_r=(0, 1.5), sl_mode=("opp", "mid")):
                    out.append(_j("build_orb", sym, tf, open_h=4.0, close_h=c, **p))
    return out


def orb_fade():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            o, c, _ = SESS[sym][tf]
            for p in grid(n_bars=(1, 2), thr=(0.6, 1.0), tp_mode=("open", "half")):
                out.append(_j("build_orb_fade", sym, tf, open_h=o, close_h=c, **p))
    return out


def gaps():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            o, c, _ = SESS[sym][tf]
            for p in grid(min_gap=(0.3, 0.6), sl_mult=(1.0, 2.0), confirm=(False, True)):
                out.append(_j("build_gap_fill", sym, tf, open_h=o, close_h=c, **p))
            for p in grid(min_gap=(0.3, 0.6), tp_atr=(0, 1.5), sl_mode=("bar", "pc")):
                out.append(_j("build_gap_go", sym, tf, open_h=o, close_h=c, **p))
    return out


def pdhl():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            o, c, _ = SESS[sym][tf]
            for p in grid(tp_atr=(0, 2.0), sl_atr=(0.75, 1.5), side=("both", "long")):
                out.append(_j("build_pdhl_break", sym, tf, open_h=o, close_h=c, **p))
            for p in grid(tp_atr=(1.5, 3.0), sl_atr=(0.5,), side=("both", "short")):
                out.append(_j("build_pdhl_fade", sym, tf, open_h=o, close_h=c, **p))
    return out


def overnight():
    out = []
    for sym in SYMS:
        o, c, _ = SESS[sym]["H1"]
        for p in grid(filt=("none", "down_day", "up_day"), sl_atr=(1.5, 3.0)):
            out.append(_j("build_overnight", sym, "H1", open_h=o, close_h=c, side="long", **p))
        out.append(_j("build_overnight", sym, "H1", open_h=o, close_h=c, side="short", sl_atr=1.5))
        out.append(_j("build_overnight", sym, "H1", open_h=o, close_h=c, side="long", sl_atr=1.5, skip_fri=True))
    return out


def drift():
    out = []
    # pre-open / fixed-hour drift seen in the hour study
    for e, hh in ((0.0, 2.0), (1.0, 2.0), (0.0, 3.0)):
        out.append(_j("build_hour_drift", "JPN225", "H1", entry_h=e, hold_h=hh, sl_atr=1.0))
    for e, hh in ((1.0, 2.0), (1.0, 3.0), (2.0, 1.0)):
        out.append(_j("build_hour_drift", "AUS200", "H1", entry_h=e, hold_h=hh, sl_atr=1.0))
    for e, hh in ((12.0, 1.0), (12.0, 2.0), (11.0, 2.0)):
        out.append(_j("build_hour_drift", "HK50", "H1", entry_h=e, hold_h=hh, sl_atr=1.0))
    for e, hh, side in ((7.0, 1.0, "short"), (10.0, 2.0, "short"), (16.0, 2.0, "long")):
        out.append(_j("build_hour_drift", "HK50", "H1", entry_h=e, hold_h=hh, sl_atr=1.0, side=side))
    out.append(_j("build_hour_drift", "AUS200", "H1", entry_h=22.0, hold_h=2.0, sl_atr=1.0, side="short"))
    # Monday effect: in at the week's first bar, out end of Monday cash / end of Monday
    for sym in SYMS:
        for hh in (8.0, 22.0):
            for sl in (1.0, 2.0):
                out.append(_j("build_hour_drift", sym, "H1", entry_h=0.0, hold_h=hh, sl_atr=sl, dows=[0]))
        out.append(_j("build_hour_drift", sym, "H1", entry_h=2.0, hold_h=6.0, sl_atr=1.0, dows=[0]))
        out.append(_j("build_hour_drift", sym, "H1", entry_h=0.0, hold_h=22.0, sl_atr=2.0, dows=[0, 2]))
    return out


def mean_rev():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            for p in grid(n=(20, 50), z_in=(2.0, 2.5), side=("both", "long")):
                out.append(_j("build_zscore_mr", sym, tf, sl_atr=1.5, max_hold=8, **p))
        for tf in ("H4", "D1"):
            for (lo, hi), tn in itertools.product(((10, 90), (25, 75)), (0, 100)):
                out.append(_j("build_rsi_mr", sym, tf, n=2, lo=lo, hi=hi, trend_n=tn, sl_atr=2.0, max_hold=5))
        for p in grid(thr=(1.0, 1.5), hold=(1, 2), side=("both", "long")):
            out.append(_j("build_daily_mr", sym, "D1", sl_atr=2.0, **p))
        for p in grid(thr=(1.5, 2.5), hold=(2, 4)):
            out.append(_j("build_daily_mr", sym, "H4", lb=1, sl_atr=2.0, side="both", **p))
    return out


def trend():
    out = []
    for sym in SYMS:
        for p in grid(n=(20, 55), trail=(2.0, 3.0), side=("both", "long")):
            out.append(_j("build_donchian", sym, "H4", **p))
        for p in grid(n=(20, 50), trail=(3.0,), side=("both", "long")):
            out.append(_j("build_donchian", sym, "D1", **p))
        for tf in ("H1", "H4"):
            for p in grid(trail=(2.0, 3.0), side=("both", "long")):
                out.append(_j("build_weekly_break", sym, tf, **p))
    return out


def us_link():
    out = []
    for sym in SYMS:
        o, c, _ = SESS[sym]["H1"]
        for p in grid(thr=(0.3, 0.6), sign=(1, -1)):
            out.append(_j("build_us_follow", sym, "H1", open_h=o, close_h=c, sl_atr=1.0, **p))
            out.append(_j("build_asia_to_us", sym, "H1", open_h=o, close_h=c, sl_atr=1.0, **p))
    return out


def ranges():
    out = []
    for sym in SYMS:
        o, c, _ = SESS[sym]["H1"]
        for nr, ins in ((4, False), (7, False), (4, True)):
            for tp in (0, 1.0):
                out.append(_j("build_nr_break", sym, "H1", nr=nr, inside=ins, open_h=o, close_h=c + 2, tp_r=tp))
    return out


def lunch():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            o, c, lh = SESS[sym][tf]
            for p in grid(thr=(0.5, 0.8), sign=(-1, 1), tp_mode=("open", "half")):
                if p["sign"] == 1 and p["tp_mode"] == "half":
                    continue
                out.append(_j("build_lunch_fade", sym, tf, open_h=o, lunch_h=lh, close_h=c, **p))
    return out


def rounds():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            for step in ROUND[sym]:
                for tp in (1.5, 3.0):
                    out.append(_j("build_round_bounce", sym, tf, step=step, tp_atr=tp, hours=[1, 11]))
    return out


def pullback():
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            o, c, _ = SESS[sym][tf]
            for p in grid(thr=(0.8, 1.2), tol=(0.2, 0.35)):
                out.append(_j("build_session_pullback", sym, tf, open_h=o, close_h=c, **p))
    return out


BATCHES = [orb, orb_fade, gaps, pdhl, overnight, drift, mean_rev, trend, us_link, ranges, lunch, rounds, pullback]


def all_jobs():
    out = []
    for b in BATCHES:
        out += b()
    return out


if __name__ == "__main__":
    for b in BATCHES:
        print(b.__name__, len(b()))
    print("total", len(all_jobs()))


def practitioner():
    """Round-3 additions: Nikkei gap-continuation EA rules, prior-session follow/fade."""
    out = []
    for sym in SYMS:
        for tf in ("M30", "H1"):
            o, c, _ = SESS[sym][tf]
            for p in grid(min_gap_pct=(0.5, 1.0), tp_r=(1.0, 2.0), be_at_1r=(True, False)):
                out.append(_j("build_gap_continuation", sym, tf, open_h=o, close_h=c, n_bars=1, window=3, **p))
            for p in grid(thr=(0.5, 1.0), sign=(1, -1), tp_atr=(0, 1.5)):
                out.append(_j("build_prev_session_follow", sym, tf, open_h=o, close_h=c, sl_atr=1.0, **p))
    return out


BATCHES.append(practitioner)


def mr_refine():
    """Widen the mean-reversion sweep around the round-3 leaders (RSI(2) on H4/D1, daily MR)."""
    out = []
    for sym in SYMS:
        for tf in ("H4", "D1"):
            for p in grid(lo_hi=((15, 85), (30, 70), (20, 80)), trend_n=(0, 50, 200), sl_atr=(1.5, 3.0), max_hold=(3, 8)):
                lo, hi = p.pop("lo_hi")
                out.append(_j("build_rsi_mr", sym, tf, n=2, lo=lo, hi=hi, **p))
            for p in grid(n=(3, 4), lo_hi=((10, 90), (25, 75)), side=("both", "long")):
                lo, hi = p.pop("lo_hi")
                out.append(_j("build_rsi_mr", sym, tf, lo=lo, hi=hi, trend_n=0, sl_atr=2.0, max_hold=5, **p))
        for p in grid(n=(2,), lo_hi=((10, 90), (25, 75)), max_hold=(8, 16)):
            lo, hi = p.pop("lo_hi")
            out.append(_j("build_rsi_mr", sym, "H1", lo=lo, hi=hi, trend_n=0, sl_atr=2.0, **p))
        for p in grid(thr=(0.75, 1.0, 1.25), hold=(2, 3), sl_atr=(1.5, 3.0), lb=(1, 2)):
            out.append(_j("build_daily_mr", sym, "D1", side="both", **p))
    return out


BATCHES.append(mr_refine)
