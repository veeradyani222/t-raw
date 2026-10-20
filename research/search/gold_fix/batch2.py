from research.search.gold_fix.runner import run
J = []
G = "XAUUSD"
# trend following
for tf in ["H4", "D1"]:
    for ne, nx in [(20, 10), (55, 20), (10, 5)]:
        J.append((f"donch{ne}_{nx}_{tf}", G, tf, "build_donchian", {"n_entry": ne, "n_exit": nx}, {}))
    J.append((f"donch20_trail3_{tf}", G, tf, "build_donchian", {"n_entry": 20, "n_exit": 0, "trail_atr": 3.0}, {}))
    J.append((f"donch20_10_long_{tf}", G, tf, "build_donchian", {"n_entry": 20, "n_exit": 10, "sides": ("long",)}, {}))
J.append(("donch55_20_H1", G, "H1", "build_donchian", {"n_entry": 55, "n_exit": 20}, {}))
J.append(("donch100_50_H1", G, "H1", "build_donchian", {"n_entry": 100, "n_exit": 50, "atr_stop": 3.0}, {}))
# session breakouts
for tf in ["H1", "M30"]:
    J.append((f"sess0-8_range_{tf}", G, tf, "build_session_break", {}, {}))
    J.append((f"sess0-8_mid_{tf}", G, tf, "build_session_break", {"stop": "mid"}, {}))
    J.append((f"sess0-8_range_tp2_{tf}", G, tf, "build_session_break", {"tp_r": 2.0}, {}))
    J.append((f"sess0-10_range_{tf}", G, tf, "build_session_break", {"range_end": 10, "entry_end": 18}, {}))
    J.append((f"sess0-15_NY_{tf}", G, tf, "build_session_break", {"range_end": 15, "entry_end": 20}, {}))
# pullback
for tf in ["H1", "H4"]:
    J.append((f"pull_rsi2_{tf}", G, tf, "build_pullback", {}, {}))
    J.append((f"pull_rsi2_long_{tf}", G, tf, "build_pullback", {"sides": ("long",)}, {}))
# hour drift
J.append(("hour1_long_hold3_H1", G, "H1", "build_hour_hold", {"hour": 1, "hold": 3}, {}))
J.append(("hour1_long_hold4_H1", G, "H1", "build_hour_hold", {"hour": 0, "hold": 4}, {}))
J.append(("hour1_long_hold3_ma200_H1", G, "H1", "build_hour_hold", {"hour": 1, "hold": 3, "ma_n": 200}, {}))
if __name__ == "__main__":
    run(J)
