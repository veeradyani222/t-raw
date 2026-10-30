"""Parameter sweeps for search3/exotics. Each batch yields
(name, build_fn, symbol, tf, params)."""
from itertools import product

from research.search3.exotics.strategies import SYMBOLS

EM = ["USDZAR", "USDMXN", "USDPLN"]
SCANDI = ["USDNOK", "USDSEK", "EURNOK", "EURSEK"]
MANAGED = ["USDSGD", "USDCNH"]


def _n(fn, sym, tf, p):
    tag = "_".join(f"{k}{v}" for k, v in p.items() if v is not None and v is not False)
    return (f"{fn}:{tag}"[:60], fn, sym, tf, p)


def trend():
    for sym, tf in product(SYMBOLS, ["D1", "H4"]):
        for n, sl, k in product([20, 55] if tf == "D1" else [30, 60, 120], [2.0, 3.0], [2.5, 4.0]):
            yield _n("donchian_trail", sym, tf, dict(n=n, sl_atr=sl, trail_k=k))
        for n, k in product([20, 60] if tf == "D1" else [60, 120, 240], [None, 3.0]):
            yield _n("tsmom", sym, tf, dict(n=n, sl_atr=2.5, trail_k=k, max_hold=None if k else n // 2))
        for f, s in [(10, 40), (20, 100), (5, 30)]:
            yield _n("ema_cross_flip", sym, tf, dict(fast=f, slow=s, sl_atr=3.0))
        yield _n("keltner_ride", sym, tf, dict(n=20, k=1.5, trend_n=100))
        yield _n("keltner_ride", sym, tf, dict(n=20, k=2.0, trend_n=50))
        for side in ("long", "short"):
            yield _n("carry_trend", sym, tf, dict(n=20, trend_n=100 if tf == "D1" else 300, side=side))


def pullback():
    for sym, tf in product(SYMBOLS, ["H4", "D1", "H1"]):
        for f, s, tp in product([20], [100, 200], [1.5, 3.0]):
            yield _n("ema_pullback", sym, tf, dict(fast=f, slow=s, tp_r=tp, max_hold=60))
        yield _n("ema_pullback", sym, tf, dict(fast=20, slow=100, tp_r=None, trail_k=2.5))
        for lo, hold in product([10, 25], [5, 10]):
            yield _n("rsi2_trend", sym, tf, dict(lo=lo, hi=100 - lo, trend_n=200, max_hold=hold))
        yield _n("rsi2_trend", sym, tf, dict(lo=10, hi=90, trend_n=100, max_hold=10, tp_r=1.5))


def breakout():
    for sym, tf in product(SYMBOLS, ["D1", "H4"]):
        for n, pct in product([20, 50], [0.3, 0.5]):
            yield _n("range_compression_break", sym, tf, dict(n=n, vol_pct=pct, trail_k=3.0))
            yield _n("range_compression_break", sym, tf, dict(n=n, vol_pct=pct, trail_k=None, tp_r=3.0))
        for pct, n in product([0.2, 0.35], [10, 20]):
            yield _n("squeeze_break", sym, tf, dict(pct=pct, n=n, tp_r=3.0, max_hold=40))
            yield _n("squeeze_break", sym, tf, dict(pct=pct, n=n, trail_k=2.5))
        for tr in (None, 100):
            yield _n("pwh_pwl_break", sym, tf, dict(trail_k=2.5, trend_n=tr))
            yield _n("pwh_pwl_break", sym, tf, dict(trail_k=None, tp_r=2.0, max_hold=30, trend_n=tr))
    for sym in SYMBOLS:
        for k, ins, tp in product([4, 7], [False, True], [1.5, 3.0]):
            yield _n("inside_day_break", sym, "D1", dict(k_nr=k, require_inside=ins, tp_r=tp, max_hold=5))


def intraday():
    for sym in SYMBOLS:
        # European morning after Asian range (CET 08-16 = server 09-17)
        for (a0, a1, t0, t1, xh), tp, mode in product([(0, 7, 8, 14, 18), (1, 8, 9, 15, 20), (3, 9, 10, 16, 22)],
                                                      [1.0, 2.0], ["atr", "range"]):
            yield _n("session_range_break", sym, "H1", dict(asia_start=a0, asia_end=a1, trade_start=t0, trade_end=t1,
                                                           exit_hour=xh, tp_r=tp, sl_mode=mode))
        for sl, tp, tr in product([0.5, 1.0], [1.5, 3.0], [None, 200]):
            yield _n("pdh_pdl_break", sym, "H1", dict(sl_atr=sl, tp_r=tp, trend_n=tr))
        for sl, tp in product([0.5, 1.0], [1.0, 2.0]):
            yield _n("pdh_pdl_fade", sym, "H1", dict(sl_atr=sl, tp_r=tp, max_hold=12))
        for mode, mm in product(["follow", "fade"], [0.3, 0.7]):
            yield _n("daily_follow", sym, "H1", dict(mode=mode, min_move_atr=mm, sl_atr=0.8))
        for mode, tp in product(["break", "fade"], [1.0, 2.0]):
            yield _n("round_number", sym, "H1", dict(mode=mode, tp_r=tp, sl_atr=1.0, max_hold=24))
        for mg in [0.15, 0.4]:
            yield _n("gap_fade", sym, "H1", dict(min_gap_atr=mg, sl_atr=1.0, tp="fill"))
            yield _n("gap_fade", sym, "H1", dict(min_gap_atr=mg, sl_atr=1.0, tp="r", tp_r=1.0, direction="follow"))


def meanrev():
    for sym, tf in product(SYMBOLS, ["H1", "H4"]):
        for n, k, ex in product([20, 50], [2.0, 2.5], ["mid", "tp"]):
            yield _n("bb_revert", sym, tf, dict(n=n, k=k, exit=ex, tp_r=1.0, max_hold=24 if tf == "H1" else 12))
        yield _n("bb_revert", sym, tf, dict(n=20, k=2.0, exit="mid", trend_n=200, trend_mode="with", max_hold=24))
    for sym, tf in product(SYMBOLS, ["D1", "H4"]):
        for mode, sp in product(["follow", "fade"], [1.5, 2.5]):
            yield _n("spike_follow", sym, tf, dict(mode=mode, spike_atr=sp, tp_r=2.0, max_hold=5 if tf == "D1" else 18))
        yield _n("spike_follow", sym, tf, dict(mode="follow", spike_atr=1.5, tp_r=2.0, max_hold=5, side_filter="long"))
        yield _n("spike_follow", sym, tf, dict(mode="fade", spike_atr=2.0, tp_r=1.5, max_hold=5, side_filter="short"))


def hours():
    # driven by the study: test the main session windows both ways with D1-trend direction
    for sym in SYMBOLS:
        for (eh, xh) in [(8, 12), (9, 16), (3, 8), (15, 20), (9, 21), (12, 18)]:
            for side in ("long", "short", "trend"):
                yield _n("hour_drift", sym, "H1", dict(enter_hour=eh, exit_hour=xh, side=side,
                                                      trend_n=200 if side == "trend" else None, sl_atr=1.0))


BATCHES = dict(trend=trend, pullback=pullback, breakout=breakout, intraday=intraday,
               meanrev=meanrev, hours=hours)




def extra():
    for sym, tf in product(SYMBOLS, ["D1", "H4"]):
        for k, tr in product([2, 4], [None, 100]):
            yield _n("swing_bos", sym, tf, dict(k=k, trend_n=tr, trail_k=3.0))
            yield _n("swing_bos", sym, tf, dict(k=k, trend_n=tr, trail_k=None, tp_r=2.0, max_hold=30))
        for n, q in product([20, 40], [0.15, 0.25]):
            yield _n("range_box_fade", sym, tf, dict(n=n, q=q, box_atr=4.0 if tf == "D1" else 6.0, max_hold=10))
        for m, tn in product([2, 3], [50, 100]):
            yield _n("three_bar_pullback", sym, tf, dict(m=m, trend_n=tn, tp_r=2.0, max_hold=15))
        yield _n("three_bar_pullback", sym, tf, dict(m=3, trend_n=50, trail_k=2.5))
        for reg, n in product(["rising", "falling"], [20, 60]):
            yield _n("vol_regime_tsmom", sym, tf, dict(n=n, regime=reg, trail_k=3.0))
    for sym in SYMBOLS:
        for w, mode in product([2, 4, 8], ["follow", "fade"]):
            yield _n("weekly_open_follow", sym, "D1", dict(weeks=w, mode=mode, sl_atr=1.5))
        for sl, tp in product([1.0, 1.5], [1.5, 2.5]):
            yield _n("pwh_pwl_fade", sym, "H4", dict(sl_atr=sl, tp_r=tp, max_hold=18))
        yield _n("pwh_pwl_fade", sym, "H1", dict(sl_atr=1.0, tp_r=1.5, max_hold=24))
        for fh, mm, mode in product([17, 18], [0.5, 1.0], ["fade", "follow"]):
            yield _n("london_fix_fade", sym, "H1", dict(fix_hour=fh, min_move_atr=mm, mode=mode, tp_r=1.0))


BATCHES["extra"] = extra


def openhour():
    # study: server hour 09 (08:00 CET, European open) has a positive mean return on every
    # USD/EUR-vs-Scandi/CEE pair (t 3.6-9.7); hour 08 is negative. Test the single hour.
    for sym in SYMBOLS:
        for eh, xh in [(9, 10), (9, 11), (8, 9), (9, 10)]:
            for side in ("long", "short"):
                for sl in (0.5, 1.0):
                    yield _n("hour_drift", sym, "H1", dict(enter_hour=eh, exit_hour=xh, side=side, sl_atr=sl))
        yield _n("hour_drift", sym, "H1", dict(enter_hour=9, exit_hour=10, side="trend", trend_n=200, sl_atr=1.0))


BATCHES["openhour"] = openhour


if __name__ == "__main__":
    for k, v in BATCHES.items():
        print(k, sum(1 for _ in v()))
