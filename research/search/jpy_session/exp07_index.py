from research.search.jpy_session.run import run
for sym,h,hold in [("US30",15,23),("US30",14,23),("US30",16,23),("US30",17,23),("US30",15,18),("US30",20,18),("US30",20,23),
                   ("US500",15,23),("US500",20,23),("DE40",15,23),("DE40",15,18)]:
    run(f"idx_long_h{h}_hold{hold}", sym, hour=h, hold=hold, side="long", sl_atr=2.0)
