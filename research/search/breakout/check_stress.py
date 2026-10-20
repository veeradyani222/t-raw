"""Cost stress (spread x1/x2) for the non-DE40 shortlist."""
from research.prop import harness as H
from research.search.breakout import strategies as S
IN = dict(kind="inside", ts=0, te=20, exit_h=None, max_hold=48, sl="far", tp_r=3.0)
cases = [("USDJPY", "H1", "build_nr_break", IN), ("GBPJPY", "H1", "build_nr_break", IN),
         ("XAUUSD", "H4", "build_donchian", dict(n_ch=55, sl_atr=3.0, trail_atr=3.0, trail_after_r=0.0, trend="d")),
         ("XAUUSD", "H4", "build_donchian", dict(n_ch=55, sl_atr=2.0, trail_atr=3.0, trail_after_r=0.0, trend="d")),
         ("GBPJPY", "H1", "build_prev_week", dict(sl_atr=1.0, trail_atr=8.0, trail_after_r=1.0, be_r=1.0))]
for sym, tf, fn, p in cases:
    df = H.load(sym, tf, split="is")
    sig = getattr(S, fn)(df, **p)
    for sm in (1.0, 2.0):
        print(H.summary_line(H.score(df, sig, spread_mult=sm, name=f"{fn[6:]} x{sm}")))
