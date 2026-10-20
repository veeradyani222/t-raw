from research.search.gold_fix.runner import run
G = "XAUUSD"
DON = ("build_mtf", {"rule": "4h", "base": "build_regime", "base_params": {"base": "build_donchian",
       "base_params": {"n_entry": 20, "n_exit": 10}, "atrp_max": 0.5, "atrp_window": 500, "adx_min": 20}})
DON_PLAIN = ("build_mtf", {"rule": "4h", "base": "build_donchian", "base_params": {"n_entry": 20, "n_exit": 10, "adx_min": 20}})
SQZ = ("build_mtf", {"rule": "4h", "base": "build_squeeze", "base_params": {}})
BOS = ("build_bos", {"tp_min_r": 2.0, "atrp_min": 0.6, "htf": ("1D", 100)})
BOS50 = ("build_bos", {"tp_min_r": 2.0, "atrp_min": 0.6, "htf": ("1D", 50)})
J = []
J.append(("combo_donLV_bos_M30", G, "M30", "build_combo", {"parts": [DON, BOS]}, {}))
J.append(("combo_bos_donLV_M30", G, "M30", "build_combo", {"parts": [BOS, DON]}, {}))
J.append(("combo_donLV_bos50_M30", G, "M30", "build_combo", {"parts": [DON, BOS50]}, {}))
J.append(("combo_donADX_bos_M30", G, "M30", "build_combo", {"parts": [DON_PLAIN, BOS]}, {}))
J.append(("combo_donLV_sqz_bos_M30", G, "M30", "build_combo", {"parts": [DON, SQZ, BOS]}, {}))
J.append(("combo_donLV_bos_M30_noflip", G, "M30", "build_combo", {"parts": [DON, BOS]}, {"allow_flip": False}))
J.append(("combo_donLV_sqz_H1", G, "H1", "build_combo", {"parts": [DON, SQZ]}, {}))
if __name__ == "__main__":
    run(J)
