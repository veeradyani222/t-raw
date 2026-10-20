from research.search.jpy_session.run import run
for hour,hold,sl in [(14,96,3.0),(12,96,3.0),(16,96,3.0),(10,96,3.0),(20,96,3.0),(14,72,3.0),(14,120,3.0),(14,48,3.0),(14,96,2.0),(14,96,4.0),(4,96,3.0)]:
    run(f"gold_tom_k0_h{hour}_hold{hold}_sl{sl:g}", "XAUUSD", fn="build_turn_of_month", k=0, hour=hour, hold=hold, sl_atr=sl)
for hour in [14,16]:
    run(f"silver_tom_k0_h{hour}_hold96_sl3", "XAGUSD", fn="build_turn_of_month", k=0, hour=hour, hold=96, sl_atr=3.0)
