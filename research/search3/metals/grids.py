"""Job grids for search3/metals. Each function returns a list of jobs."""
from itertools import product

SYMS = ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD"]
STEPS = {"XAUUSD": (50.0, 100.0), "XAGUSD": (0.5, 1.0), "XPTUSD": (25.0, 50.0), "XPDUSD": (25.0, 50.0)}


def _j(name, fn, sym, tf, **p):
    return dict(name=name, fn=fn, symbol=sym, tf=tf, params=p)


def asia_break():
    jobs = []
    wins = [("mql", 3, 8, 14, 21), ("asia10", 1, 10, 16, 22), ("ldn_orb", 10, 11, 16, 22), ("ny_orb", 16, 17, 21, 22)]
    for sym, tf, (wn, a0, a1, le, xh), tp, stop, mr in product(
            SYMS, ["M30", "H1"], wins, ["r:2.5", "pdhl", "range"], ["range", "mid"], [0.3, 0.0]):
        jobs.append(_j(f"ab_{wn}_{tp}_{stop}_mr{mr}", "build_asia_break", sym, tf,
                       a0=a0, a1=a1, last_entry=le, exit_hour=xh, tp=tp, stop=stop, min_rng=mr,
                       max_rng=1.6 if mr else 99.0, be_r=1.5 if stop == "range" else None))
    return jobs


def asia_fade():
    jobs = []
    for sym, tf, (a0, a1, le), tp in product(SYMS, ["M30", "H1"], [(1, 10, 16), (3, 8, 14)], ["other", "mid", "r:1.5"]):
        jobs.append(_j(f"af_{a0}-{a1}_{tp}", "build_asia_fade", sym, tf, a0=a0, a1=a1, last_entry=le, tp=tp))
    return jobs


def pd_sweep():
    jobs = []
    for sym, tf, lvl, tp in product(SYMS, ["M30", "H1"], ["pd", "pw"], ["mid", "other", "r:1.5", "r:2.5"]):
        jobs.append(_j(f"ps_{lvl}_{tp}", "build_pd_sweep", sym, tf, level=lvl, tp=tp))
    for sym, tp in product(SYMS, ["mid", "other", "r:1.5", "r:2.5"]):
        jobs.append(_j(f"ps_pw_{tp}_h4", "build_pd_sweep", sym, "H4", level="pw", tp=tp, h0=0, h1=23, max_hold=30, exit_hour=None))
    return jobs


def pd_break():
    jobs = []
    for sym, tf, stop, tp, be in product(SYMS, ["M30", "H1"], ["atr:1.0", "mid", "pdc"], ["range", "r:1.5", "r:3"], [None, 1.0]):
        jobs.append(_j(f"pb_{stop}_{tp}_be{be}", "build_pd_break", sym, tf, stop=stop, tp=tp, be_r=be))
    return jobs


def session_hold():
    jobs = []
    longs = [(22, 9), (23, 9), (1, 9), (22, 12), (1, 12), (2, 9), (2, 15), (21, 3)]
    shorts = [(15, 22), (12, 22), (10, 15), (9, 22), (16, 22), (15, 1)]
    for sym, (hi, ho), st, dows in product(SYMS, longs, [1.5, 3.0], [None, (0,), (0, 1), (0, 1, 2)]):
        jobs.append(_j(f"sh_long_{hi}-{ho}_s{st}_d{dows}", "build_session_hold", sym, "H1", side="long", h_in=hi, h_out=ho, stop_atr=st, dows=dows))
    for sym, (hi, ho), st, dows in product(SYMS, shorts, [1.5, 3.0], [None, (3, 4)]):
        jobs.append(_j(f"sh_short_{hi}-{ho}_s{st}_d{dows}", "build_session_hold", sym, "H1", side="short", h_in=hi, h_out=ho, stop_atr=st, dows=dows))
    return jobs


def ratio_z():
    jobs = []
    pairs = [("XAUUSD", "XAGUSD"), ("XAGUSD", "XAUUSD"), ("XPTUSD", "XPDUSD"), ("XPDUSD", "XPTUSD"),
             ("XAUUSD", "XPTUSD"), ("XPTUSD", "XAUUSD"), ("XAGUSD", "XPTUSD"), ("XPDUSD", "XAUUSD")]
    for (sym, oth), tf, zn, zi in product(pairs, ["H1", "H4", "D1"], [100, 200], [2.0, 2.5]):
        mh = {"H1": 30, "H4": 30, "D1": 10}[tf]
        jobs.append(_j(f"rz_{oth}_n{zn}_z{zi}", "build_ratio_z", sym, tf, other=oth, z_n=zn, z_in=zi, max_hold=mh))
    for (sym, oth), tf in product(pairs, ["H1", "H4"]):
        jobs.append(_j(f"rz_{oth}_n200_z2.5_zout0.5", "build_ratio_z", sym, tf, other=oth, z_n=200, z_in=2.5, max_hold=60, z_out=0.5, tp_r=3.0))
    return jobs


def lag_catchup():
    jobs = []
    pairs = [("XAGUSD", "XAUUSD"), ("XPTUSD", "XAUUSD"), ("XPDUSD", "XAUUSD"), ("XAUUSD", "XAGUSD"), ("XPDUSD", "XPTUSD")]
    for (sym, ld), tf, n, zi, mode in product(pairs, ["H1", "H4"], [6, 24], [1.5, 2.0], ["follow", "fade"]):
        jobs.append(_j(f"lc_{ld}_n{n}_z{zi}_{mode}", "build_lag_catchup", sym, tf, leader=ld, n=n, z_in=zi, mode=mode))
    return jobs


def round_level():
    jobs = []
    for sym in SYMS:
        for step, tf, mode, sf, tp in product(STEPS[sym], ["M30", "H1"], ["break", "fade"], [0.2, 0.3], ["next", "r:1.5"]):
            jobs.append(_j(f"rl_{mode}_s{step}_sf{sf}_{tp}", "build_round_level", sym, tf, step=step, mode=mode, stop_frac=sf, tp=tp))
    return jobs


def nr_break():
    jobs = []
    for sym, (nr, ins), stop, tp in product(SYMS, [(4, False), (7, False), (7, True)], ["mid", "other", "atr:1.0"], ["range", "r:2"]):
        jobs.append(_j(f"nr_{'inside' if ins else nr}_{stop}_{tp}", "build_nr_break", sym, "H1", nr=nr, inside=ins, stop=stop, tp=tp))
    return jobs


def fix_fade():
    jobs = []
    for sym, tf, fix, lb, k, mode in product(SYMS, ["M30", "H1"], ["am", "pm"], [2, 4], [0.5, 1.0], ["fade", "follow"]):
        xh = 16 if fix == "am" else 20
        jobs.append(_j(f"ff_{fix}_lb{lb}_k{k}_{mode}", "build_fix_fade", sym, tf, fix=fix, lookback_h=lb, k_atr=k, mode=mode, exit_hour=xh))
    return jobs


def late_day():
    jobs = []
    for sym, ch, q, pd_, mode in product(SYMS, [16, 17, 18], [0.75, 0.85], [True, False], ["follow", "fade"]):
        jobs.append(_j(f"ld_h{ch}_q{q}_pd{pd_}_{mode}", "build_late_day", sym, "H1", check_hour=ch, q=q, need_pd=pd_, mode=mode))
    return jobs


def gap_fade():
    jobs = []
    for sym, k, mode, mon, tp in product(SYMS, [0.3, 0.6, 1.0], ["fade", "follow"], [False, True], ["fill", "r:1.5"]):
        if mode == "follow" and tp == "fill":
            tp = "r:1.5"
        jobs.append(_j(f"gf_k{k}_{mode}_mon{mon}_{tp}", "build_gap_fade", sym, "H1", k_atr=k, mode=mode, monday_only=mon, tp=tp))
    return jobs


def asia_dip():
    jobs = []
    for sym, tn, dip, tp, side in product(SYMS, [10, 20], [0.3, 0.6, 1.0], ["pdh", "pdc", "r:1.5"], ["both", "long"]):
        jobs.append(_j(f"ad_t{tn}_d{dip}_{tp}_{side}", "build_asia_dip", sym, "H1", trend_n=tn, dip_atr=dip, tp=tp, side=side))
    return jobs


def d1_reversal():
    jobs = []
    for sym, tf, k, mode, st in product(SYMS, ["D1", "H4"], [0.8, 1.2], ["fade", "follow"], [1.5, 2.5]):
        holds = [1, 2, 3] if tf == "D1" else [6, 12]
        for hold in holds:
            jobs.append(_j(f"dr_k{k}_{mode}_h{hold}_s{st}", "build_d1_reversal", sym, tf, k_atr=k, mode=mode, hold=hold, stop_atr=st))
    return jobs


def wopen():
    jobs = []
    for sym, tf, md, tol, tp in product(SYMS, ["H1", "H4"], [1.0, 2.0], [0.2, 0.3], ["wext", "r:2"]):
        jobs.append(_j(f"wo_d{md}_t{tol}_{tp}", "build_wopen_retest", sym, tf, min_dist_atr=md, tol_atr=tol, tp=tp,
                       max_hold=48 if tf == "H1" else 12))
    return jobs


def channel():
    jobs = []
    for sym, (nl, ns), st, tpr, side in product(SYMS, [(6, 2), (6, 6), (12, 4), (24, 24)], [1.5, 2.5], [1.5, 2.5], ["both", "long", "short"]):
        jobs.append(_j(f"ch_{nl}-{ns}_s{st}_tp{tpr}_{side}", "build_channel_pt", sym, "H1", n_long=nl, n_short=ns, stop_atr=st, tp_r=tpr, side=side))
    for sym, (nl, ns), tr in product(SYMS, [(6, 2), (24, 24)], [2.0, 3.0]):
        jobs.append(_j(f"ch_{nl}-{ns}_trail{tr}", "build_channel_pt", sym, "H1", n_long=nl, n_short=ns, stop_atr=2.0, trail_atr=tr, max_hold=48))
    return jobs


def unger_pt():
    """Unger platinum morning-weakness bias: short 04:00-09:00 Chicago = 12/13-17/18
    server; optional prior-day-down filter. Applied to all four metals, plus the
    mirror (long) and the CBS 'hat-shape' Asia-long / West-short clock."""
    jobs = []
    for sym, (hi, ho), st, pdf in product(SYMS, [(12, 17), (13, 18), (12, 18), (11, 16)], [1.5, 3.0], [None, "down"]):
        jobs.append(_j(f"up_short_{hi}-{ho}_s{st}_pd{pdf}", "build_session_hold", sym, "H1", side="short", h_in=hi, h_out=ho, stop_atr=st, prev_day=pdf))
    for sym, (hi, ho), st, pdf in product(SYMS, [(1, 9), (23, 9)], [1.5, 3.0], ["down", "up"]):
        jobs.append(_j(f"up_long_{hi}-{ho}_s{st}_pd{pdf}", "build_session_hold", sym, "H1", side="long", h_in=hi, h_out=ho, stop_atr=st, prev_day=pdf))
    return jobs


ALL = ["unger_pt", "asia_break", "asia_fade", "pd_sweep", "pd_break", "session_hold", "ratio_z", "lag_catchup",
       "round_level", "nr_break", "fix_fade", "late_day", "gap_fade", "asia_dip", "d1_reversal", "wopen", "channel"]
