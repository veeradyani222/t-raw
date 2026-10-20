"""Grid 4: try to cut gold-H4 Donchian drawdown (day-trend filter, vol filter,
exit tweaks, other entry styles with the same exit) + USDJPY/US30 H1 day-filtered breakouts."""
from research.search.trend.run import run


def configs():
    g = []
    X = ("XAUUSD", "H4")
    for dn in (20, 50, 100):
        g.append((f"htf_bo{dn}_n80_x20_sl3", "build_htf_breakout", *X, dict(d_n=dn, n_entry=80, n_exit=20, sl_mult=3.0)))
    g.append(("htf_ema50_n80_x20_sl3", "build_htf_breakout", *X, dict(d_kind="ema", d_n=50, n_entry=80, n_exit=20, sl_mult=3.0)))
    for r in (0.9, 1.0, 1.2):
        g.append((f"donch80_volx{r}_sl3", "build_donchian_volx", *X, dict(n_entry=80, ratio=r, sl_mult=3.0)))
    for nx in (10, 40):
        g.append((f"donch80_{nx}_sl3.0", "build_donchian", *X, dict(n_entry=80, n_exit=nx, sl_mult=3.0)))
    for tr in (2.5, 3.5):
        g.append((f"donch80_20_sl3.0_tr{tr}", "build_donchian", *X, dict(n_entry=80, n_exit=20, sl_mult=3.0, trail_mult=tr)))
    g.append(("donch80_20_sl3.0_atr50", "build_donchian", *X, dict(n_entry=80, n_exit=20, sl_mult=3.0, atr_n=50)))
    for nm, fn, p in (("keltner50_2_sl3", "build_keltner_bo", dict(n=50, k=2.0)),
                      ("boll50_2_sl3", "build_bollinger_bo", dict(n=50, k=2.0)),
                      ("ema20_100_sl3", "build_ma_cross", dict(fast=20, slow=100)),
                      ("ichimoku_sl3", "build_ichimoku", dict()),
                      ("supertrend20_4_sl3", "build_supertrend", dict(st_n=20, st_mult=4.0))):
        g.append((nm, fn, *X, dict(p, sl_mult=3.0)))
    # gold H4 rule at D1 & on H1 with 4x lengths (same horizon)
    g.append(("donch320_80_sl3.0", "build_donchian", "XAUUSD", "H1", dict(n_entry=320, n_exit=80, sl_mult=3.0)))
    g.append(("donch20_5_sl3.0", "build_donchian", "XAUUSD", "D1", dict(n_entry=20, n_exit=5, sl_mult=3.0)))
    # day-filtered H1 breakouts where grid 3 showed raw R edge
    for sym in ("USDJPY", "US30"):
        for dn in (20, 100):
            g.append((f"htf_bo{dn}_n48_sl3", "build_htf_breakout", sym, "H1", dict(d_n=dn, n_entry=48, sl_mult=3.0)))
        g.append(("htf_bo50_n96_sl3", "build_htf_breakout", sym, "H1", dict(d_n=50, n_entry=96, sl_mult=3.0)))
        g.append(("htf_bo50_n48_x24_sl3", "build_htf_breakout", sym, "H1", dict(d_n=50, n_entry=48, n_exit=24, sl_mult=3.0)))
    # D1-filtered H4 breakouts on the other H4 trenders
    for sym in ("USDJPY", "GBPJPY", "AUDJPY", "US30"):
        g.append(("htf_bo50_n80_x20_sl3", "build_htf_breakout", sym, "H4", dict(d_n=50, n_entry=80, n_exit=20, sl_mult=3.0)))
        g.append(("donch80_20_sl3.0", "build_donchian", sym, "H4", dict(n_entry=80, n_exit=20, sl_mult=3.0)))
    return g


if __name__ == "__main__":
    cf = configs()
    print(len(cf), "configs")
    run(cf)
