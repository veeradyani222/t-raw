from research.search.gold_fix.runner import run
G = "XAUUSD"
LN = list(range(7, 22))
J = []
b = {"tp_min_r": 2.0, "atrp_min": 0.6}
J.append(("bos_hv_htf_noflip_M30", G, "M30", "build_bos", {**b, "htf": ("1D", 50)}, {"allow_flip": False}))
J.append(("bos_hv_htf_LN_M30", G, "M30", "build_bos", {**b, "htf": ("1D", 50), "hours": LN}, {}))
J.append(("bos_hv_htfD20_M30", G, "M30", "build_bos", {**b, "htf": ("1D", 20)}, {}))
J.append(("bos_hv_htfD100_M30", G, "M30", "build_bos", {**b, "htf": ("1D", 100)}, {}))
J.append(("bos_hv_htfH4_50_M30", G, "M30", "build_bos", {**b, "htf": ("4h", 50)}, {}))
J.append(("bos_hv_be1_M30", G, "M30", "build_bos", {**b, "be_r": 1.0}, {}))
J.append(("bos_hv_nocmf_M30", G, "M30", "build_bos", {**b, "use_cmf": False}, {}))
J.append(("bos_hv_noma_M30", G, "M30", "build_bos", {**b, "trend_ma": 0}, {}))
J.append(("bos_hv_sw3_M30", G, "M30", "build_bos", {**b, "swing_window": 3}, {}))
J.append(("bos_hv_fixR2_M30", G, "M30", "build_bos", {"tp_mode": "fixed", "tp_r": 2.0, "atrp_min": 0.6}, {}))
J.append(("bos_hv_M15", G, "M15", "build_bos", {**b}, {}))
J.append(("bos_hv_htf_H1", G, "H1", "build_bos", {**b, "htf": ("1D", 50)}, {}))
J.append(("donch20_10_adx20_stop3_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 10, "adx_min": 20, "atr_stop": 3.0}, {}))
J.append(("donch20_10_adx20_trail4_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 10, "adx_min": 20, "trail_atr": 4.0}, {}))
J.append(("donch20_10_adx20_long_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 10, "adx_min": 20, "sides": ("long",)}, {}))
J.append(("donch30_10_adx20_H4", G, "H4", "build_donchian", {"n_entry": 30, "n_exit": 10, "adx_min": 20}, {}))
J.append(("donch15_10_adx20_H4", G, "H4", "build_donchian", {"n_entry": 15, "n_exit": 10, "adx_min": 20}, {}))
J.append(("donch20_15_adx20_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 15, "adx_min": 20}, {}))
if __name__ == "__main__":
    run(J)
