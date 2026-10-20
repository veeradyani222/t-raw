from research.search.jpy_session.run import run
J=["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","CADJPY","USDJPY"]
for sym in J:
    run("live_h0_hold12", sym, fn="build_chfjpy_live")
for sym in ["CHFJPY","EURJPY"]:
    run("h1_long_hold12", sym, hour=1, hold=12, side="long")
for sym in ["EURJPY","AUDJPY","USDJPY","GBPJPY"]:
    run("mon_long_h0_hold47", sym, hour=0, hold=47, side="long", weekdays=(0,))
    run("mon_long_h0_hold36_downweek", sym, hour=0, hold=36, side="long", weekdays=(0,), prior_n=120, prior_dir="down")
for sym in ["EURJPY","AUDJPY"]:
    run("mon_long_h0_hold23", sym, hour=0, hold=23, side="long", weekdays=(0,))
    run("mon_long_h4_hold36", sym, hour=4, hold=36, side="long", weekdays=(0,))
    run("mon_long_h0_hold36_sl3", sym, hour=0, hold=36, side="long", sl_atr=3.0, weekdays=(0,))
for sym in ["EURJPY","GBPJPY","AUDJPY","NZDJPY"]:
    run("week_monlong_frishort", sym, fn="build_multi_session", legs=[
        dict(hour=0, hold=36, side="long", weekdays=(0,)),
        dict(hour=1, hold=22, side="short", weekdays=(4,), d1_ma=200)])
for sym in ["US30","US500","DE40"]:
    run("idx_long_h20_hold18_d1ma200", sym, hour=20, hold=18, side="long", d1_ma=200)
    run("idx_long_h15_hold23_d1ma50", sym, hour=15, hold=23, side="long", d1_ma=50)
