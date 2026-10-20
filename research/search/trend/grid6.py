"""Grid 6: cross-symbol check of the gold-H4 Bollinger winner + D1 Donchian/tsmom gold long-only cross-check."""
from research.search.trend.run import run

if __name__ == "__main__":
    g = []
    for sym, tf in (("XAGUSD", "H4"), ("XAUUSD", "D1"), ("EURJPY", "H4"), ("CADJPY", "H4"),
                    ("GBPUSD", "H4"), ("US500", "H4"), ("USTEC", "H4"), ("EURUSD", "H4"), ("XAUUSD", "H1")):
        g.append(("boll50_2.0_sl3.0", "build_bollinger_bo", sym, tf, dict(n=50, k=2.0, sl_mult=3.0)))
    g.append(("boll200_2.0_sl3.0", "build_bollinger_bo", "XAUUSD", "H1", dict(n=200, k=2.0, sl_mult=3.0)))
    g.append(("boll50_2.0_sl3.0_long", "build_bollinger_bo", "XAUUSD", "H4", dict(n=50, k=2.0, sl_mult=3.0, long_only=True)))
    g.append(("boll50_2.0_sl3.0_short", "build_bollinger_bo", "XAUUSD", "H4", dict(n=50, k=2.0, sl_mult=3.0, short_only=True)))
    g.append(("boll50_2.0_sl3.0_ema200", "build_bollinger_bo", "XAUUSD", "H4", dict(n=50, k=2.0, sl_mult=3.0, trend_ema=200)))
    g.append(("boll50_2.0_sl3.0_tr4", "build_bollinger_bo", "XAUUSD", "H4", dict(n=50, k=2.0, sl_mult=3.0, trail_mult=4.0)))
    g.append(("boll50_2.0_sl3.0_notrail", "build_bollinger_bo", "XAUUSD", "H4", dict(n=50, k=2.0, sl_mult=3.0, trail_mult=None)))
    run(g)
