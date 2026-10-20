from research.search.jpy_session.run import run
for sym in ["GBPJPY","EURJPY","USDJPY","XAUUSD","GBPUSD","EURUSD"]:
    run("asia_bo_0-6_to14_x21", sym, fn="build_session_breakout")
for sym in ["GBPJPY","XAUUSD"]:
    run("asia_bo_0-6_to14_x21_tp2", sym, fn="build_session_breakout", tp_r=2.0)
    run("asia_bo_0-6_to14_x21_d1ma50", sym, fn="build_session_breakout", d1_ma=50)
    run("asia_bo_0-8_to16_x22_half", sym, fn="build_session_breakout", range_end=8, last_entry=16, exit_hour=22, sl_frac=0.5)
