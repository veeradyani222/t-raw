from research.search.jpy_session.run import run
for sym in ["US500","US30","DE40"]:
    for hour,hold,sl in [(22,72,3.0),(20,72,3.0),(22,48,3.0),(22,96,3.0),(22,72,5.0),(22,24,3.0)]:
        run(f"tom_k0_h{hour}_hold{hold}_sl{int(sl)}", sym, fn="build_turn_of_month", k=0, hour=hour, hold=hold, sl_atr=sl)
