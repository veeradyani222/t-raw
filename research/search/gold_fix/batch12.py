from research.search.gold_fix.runner import run
G = "XAUUSD"
B = {"tp_min_r": 2.0, "atrp_min": 0.6, "htf": ("1D", 100)}
J = [
    ("bos_hvD100_trail3_M30", G, "M30", "build_bos", {**B, "tp_mode": "none", "trail_atr": 3.0}, {}),
    ("bos_hvD100_trail5_M30", G, "M30", "build_bos", {**B, "tp_mode": "none", "trail_atr": 5.0}, {}),
    ("bos_hvD100_long_M30", G, "M30", "build_bos", {**B, "sides": ("long",)}, {}),
    ("bos_hvD100_stopatr1.5_M30", G, "M30", "build_bos", {**B, "stop_atr_min": 1.5}, {}),
    ("bos_hvD100_atrp0.5_M30", G, "M30", "build_bos", {**B, "atrp_min": 0.5}, {}),
    ("bos_hvD100_atrp0.7_M30", G, "M30", "build_bos", {**B, "atrp_min": 0.7}, {}),
    ("bos_hvD100_noflip_M30", G, "M30", "build_bos", B, {"allow_flip": False}),
    ("bos_hvD100_spread2x_M30", G, "M30", "build_bos", B, {"spread_mult": 2.0}),
    ("bos_hvD100_M30_XAG", "XAGUSD", "M30", "build_bos", B, {}),
    ("squeeze_x7_tr5_H4", G, "H4", "build_squeeze", {"n_exit": 7, "trail_atr": 5.0}, {}),
    ("squeeze_x7_H4", G, "H4", "build_squeeze", {"n_exit": 7}, {}),
    ("squeeze_adx_x7_tr5_H4", G, "H4", "build_regime", {"base": "build_squeeze", "base_params": {"n_exit": 7, "trail_atr": 5.0}, "adx_min": 20}, {}),
    ("squeeze_x7_tr5_H4_XAG", "XAGUSD", "H4", "build_squeeze", {"n_exit": 7, "trail_atr": 5.0}, {}),
]
if __name__ == "__main__":
    run(J)
