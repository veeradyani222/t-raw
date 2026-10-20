from research.search.gold_fix.runner import run
G = "XAUUSD"
LN = list(range(7, 22))  # London + NY server hours (skip thin Asian/rollover hours)
J = []
for tf in ["M30", "H1"]:
    J += [
        (f"bos_LN_{tf}", G, tf, "build_bos", {"hours": LN}, {}),
        (f"bos_LN_tpmin2_{tf}", G, tf, "build_bos", {"hours": LN, "tp_min_r": 2.0}, {}),
        (f"bos_htfD50_{tf}", G, tf, "build_bos", {"htf": ("1D", 50)}, {}),
        (f"bos_htfD50_tpmin2_{tf}", G, tf, "build_bos", {"htf": ("1D", 50), "tp_min_r": 2.0}, {}),
        (f"bos_trail3_{tf}", G, tf, "build_bos", {"tp_mode": "none", "trail_atr": 3.0}, {}),
        (f"bos_trail3_htfD50_{tf}", G, tf, "build_bos", {"tp_mode": "none", "trail_atr": 3.0, "htf": ("1D", 50)}, {}),
        (f"bos_tpmin2_noflip_{tf}", G, tf, "build_bos", {"tp_min_r": 2.0}, {"allow_flip": False}),
    ]
for ap in [0.4, 0.5, 0.7, 0.8]:
    J.append((f"bos_tpmin2_atrp{ap}_M30", G, "M30", "build_bos", {"tp_min_r": 2.0, "atrp_min": ap}, {}))
J.append(("bos_tpmin1.5_atrp0.6_M30", G, "M30", "build_bos", {"tp_min_r": 1.5, "atrp_min": 0.6}, {}))
J.append(("bos_tpmin2.5_atrp0.6_M30", G, "M30", "build_bos", {"tp_min_r": 2.5, "atrp_min": 0.6}, {}))
J.append(("bos_tpmin2_atrp0.6_LN_M30", G, "M30", "build_bos", {"tp_min_r": 2.0, "atrp_min": 0.6, "hours": LN}, {}))
J.append(("bos_tpmin2_atrp0.6_htf_M30", G, "M30", "build_bos", {"tp_min_r": 2.0, "atrp_min": 0.6, "htf": ("1D", 50)}, {}))
J.append(("bos_tpmin2_atrp0.6_noflip_M30", G, "M30", "build_bos", {"tp_min_r": 2.0, "atrp_min": 0.6}, {"allow_flip": False}))
J.append(("bos_tpmin2_atrp0.6_M30_XAG", "XAGUSD", "M30", "build_bos", {"tp_min_r": 2.0, "atrp_min": 0.6}, {}))
if __name__ == "__main__":
    run(J)
