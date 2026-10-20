"""Grid 2: neighbourhoods around the families that worked in grid 1
(XAUUSD H4/D1, USDJPY H4/D1, GBPUSD D1) - one factor at a time."""
import sys

from research.search.trend.run import run

TARGETS = [("XAUUSD", "H4"), ("XAUUSD", "D1"), ("USDJPY", "H4"), ("USDJPY", "D1"), ("GBPUSD", "D1")]


def configs():
    out = []
    for sym, tf in TARGETS:
        # Donchian entry / exit lengths
        for ne in (20, 40, 55, 80, 120):
            for nx in (10, 20, 40):
                if nx < ne:
                    out.append((f"donch{ne}_{nx}", "build_donchian", sym, tf, dict(n_entry=ne, n_exit=nx)))
        # exit machinery on donchian 55/20
        for slm in (1.5, 3.0):
            out.append((f"donch55_20_sl{slm}", "build_donchian", sym, tf, dict(n_entry=55, n_exit=20, sl_mult=slm)))
        for tr in (2.0, 4.0, 6.0):
            out.append((f"donch55_20_tr{tr}", "build_donchian", sym, tf, dict(n_entry=55, n_exit=20, trail_mult=tr)))
        out.append(("donch55_20_notrail", "build_donchian", sym, tf, dict(n_entry=55, n_exit=20, trail_mult=None)))
        # time-series momentum lookbacks + state mode (re-entry while trend on)
        for lb in (20, 50, 100, 200):
            out.append((f"tsmom{lb}", "build_tsmom", sym, tf, dict(lookback=lb)))
            out.append((f"tsmom{lb}_state", "build_tsmom", sym, tf, dict(lookback=lb, mode="state")))
        # EMA cross neighbours
        for f, s in ((10, 50), (20, 100), (50, 200), (20, 50)):
            out.append((f"ema{f}_{s}", "build_ma_cross", sym, tf, dict(fast=f, slow=s)))
        # long only (asymmetric drift check)
        out.append(("donch55_20_long", "build_donchian", sym, tf, dict(n_entry=55, n_exit=20, long_only=True)))
        out.append(("tsmom50_long", "build_tsmom", sym, tf, dict(lookback=50, long_only=True)))
        # trend filter
        out.append(("donch55_20_ema200", "build_donchian", sym, tf, dict(n_entry=55, n_exit=20, trend_ema=200)))
        out.append(("donch55_20_adx20", "build_donchian", sym, tf, dict(n_entry=55, n_exit=20, adx_min=20)))
    return out


if __name__ == "__main__":
    cf = configs()
    if len(sys.argv) > 1:
        cf = [c for c in cf if c[2] == sys.argv[1]]
    print(len(cf), "configs")
    run(cf)
