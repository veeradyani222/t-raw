"""Grid 3: (A) gold H4 Donchian neighbourhood around the grid-2 sweet spot,
(B) does the best H4 rule carry to other trending symbols, (C) H1 entries
filtered by the closed-day trend (breakout + pullback)."""
from research.search.trend.run import run


def configs():
    out = []
    # A: gold H4 neighbourhood
    for ne in (80, 100, 120, 150):
        for slm in (2.0, 3.0, 4.0):
            out.append((f"donch{ne}_20_sl{slm}", "build_donchian", "XAUUSD", "H4",
                        dict(n_entry=ne, n_exit=20, sl_mult=slm)))
    for ne in (80, 120):
        out.append((f"donch{ne}_20_sl3.0_tr4", "build_donchian", "XAUUSD", "H4",
                    dict(n_entry=ne, n_exit=20, sl_mult=3.0, trail_mult=4.0)))
        out.append((f"donch{ne}_20_sl3.0_long", "build_donchian", "XAUUSD", "H4",
                    dict(n_entry=ne, n_exit=20, sl_mult=3.0, long_only=True)))
    # B: carry the rule to other symbols
    for sym in ("USDJPY", "GBPJPY", "AUDJPY", "EURJPY", "CADJPY", "CHFJPY", "US30", "US500",
                "USTEC", "XAGUSD", "GBPUSD", "EURUSD"):
        out.append(("donch100_20_sl3.0", "build_donchian", sym, "H4", dict(n_entry=100, n_exit=20, sl_mult=3.0)))
        out.append(("donch55_20_sl3.0", "build_donchian", sym, "H4", dict(n_entry=55, n_exit=20, sl_mult=3.0)))
    # C: H1 entries in the closed-day trend direction
    for sym in ("XAUUSD", "USDJPY", "GBPJPY", "AUDJPY", "US30"):
        out.append(("htf_bo50_n24", "build_htf_breakout", sym, "H1", dict(d_n=50, n_entry=24)))
        out.append(("htf_bo50_n24_h8_20", "build_htf_breakout", sym, "H1", dict(d_n=50, n_entry=24, hours=(8, 20))))
        out.append(("htf_bo50_n48_sl3", "build_htf_breakout", sym, "H1", dict(d_n=50, n_entry=48, sl_mult=3.0)))
        out.append(("htf_pb50_rsi2_tp1.5", "build_htf_pullback", sym, "H1",
                    dict(d_n=50, rsi_n=2, rsi_lo=10, sl_mult=2.0, tp_mult=1.5, trail_mult=None, max_hold=24)))
        out.append(("htf_pb50_rsi2_trail", "build_htf_pullback", sym, "H1",
                    dict(d_n=50, rsi_n=2, rsi_lo=10, sl_mult=2.0, trail_mult=3.0)))
    return out


if __name__ == "__main__":
    cf = configs()
    print(len(cf), "configs")
    run(cf)
