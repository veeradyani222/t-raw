from research.search.jpy_session.run import run
syms=["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]
for sym in syms:
    run(f"mon_long_h0_sl2_hold36", sym, hour=0, hold=36, side="long", sl_atr=2.0, weekdays=(0,))
for sym in syms:
    run(f"fri_short_h1_sl2_hold22_d1ma200", sym, hour=1, hold=22, side="short", sl_atr=2.0, weekdays=(4,), d1_ma=200)
