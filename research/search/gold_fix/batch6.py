from research.search.gold_fix.runner import run
G = "XAUUSD"
J = []
for ap in [0.5, 0.7]:
    for tf in ["H1", "M30"]:
        J.append((f"sess0-8_range_atrp{ap}_{tf}", G, tf, "build_regime",
                  {"base": "build_session_break", "base_params": {}, "atrp_min": ap}, {}))
J.append(("sess0-8_range_tp2_atrp0.6_H1", G, "H1", "build_regime",
          {"base": "build_session_break", "base_params": {"tp_r": 2.0}, "atrp_min": 0.6}, {}))
J.append(("donch20_10_atrp0.5_H4", G, "H4", "build_regime",
          {"base": "build_donchian", "base_params": {"n_entry": 20, "n_exit": 10}, "atrp_min": 0.5, "atrp_window": 500}, {}))
J.append(("donch20_10_atrpmax0.5_H4", G, "H4", "build_regime",
          {"base": "build_donchian", "base_params": {"n_entry": 20, "n_exit": 10}, "atrp_max": 0.5, "atrp_window": 500}, {}))
for tf in ["H4", "H1"]:
    J.append((f"squeeze_{tf}", G, tf, "build_squeeze", {}, {}))
    J.append((f"squeeze_trail3_{tf}", G, tf, "build_squeeze", {"trail_atr": 3.0}, {}))
    J.append((f"squeeze_sq0.1_{tf}", G, tf, "build_squeeze", {"sq_pct": 0.1}, {}))
    J.append((f"squeeze_sq0.3_{tf}", G, tf, "build_squeeze", {"sq_pct": 0.3}, {}))
J.append(("squeeze_M30", G, "M30", "build_squeeze", {}, {}))
J.append(("squeeze_H4_XAG", "XAGUSD", "H4", "build_squeeze", {}, {}))
J.append(("pull_rsi2_atrp0.6_H1", G, "H1", "build_regime", {"base": "build_pullback", "base_params": {}, "atrp_min": 0.6}, {}))
J.append(("pull_rsi2_adxmax20_H1", G, "H1", "build_regime", {"base": "build_pullback", "base_params": {}, "adx_max": 20}, {}))
if __name__ == "__main__":
    run(J)
