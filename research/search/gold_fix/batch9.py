from research.search.gold_fix.runner import run
G = "XAUUSD"
J = []
def lv(ne=20, nx=10, stop=2.0, am=0.5, w=500, adx=20, trail=None):
    bp = {"n_entry": ne, "n_exit": nx, "atr_stop": stop}
    if trail:
        bp["trail_atr"] = trail
    p = {"base": "build_donchian", "base_params": bp, "atrp_max": am, "atrp_window": w}
    if adx:
        p["adx_min"] = adx
    return p
for st in [2.5, 3.0, 4.0]:
    J.append((f"donLV_adx20_stop{st}_H4", G, "H4", "build_regime", lv(stop=st), {}))
for nx in [7, 12]:
    J.append((f"donLV_adx20_x{nx}_H4", G, "H4", "build_regime", lv(nx=nx), {}))
J.append(("donLV_adx20_trail5_H4", G, "H4", "build_regime", lv(trail=5.0), {}))
J.append(("donLV_adx15_H4", G, "H4", "build_regime", lv(adx=15), {}))
J.append(("donLV_adx25_H4", G, "H4", "build_regime", lv(adx=25), {}))
J.append(("donLV15_adx20_H4", G, "H4", "build_regime", lv(ne=15), {}))
J.append(("donLV30_adx20_H4", G, "H4", "build_regime", lv(ne=30), {}))
for rule, w in [("2h", 1000), ("6h", 330), ("8h", 250), ("12h", 170)]:
    J.append((f"donLV_adx20_mtf{rule}_H1", G, "H1", "build_mtf", {"rule": rule, "base": "build_regime", "base_params": lv(w=w)}, {}))
J.append(("donLV_adx20_H4_XAG", "XAGUSD", "H4", "build_regime", lv(), {}))
J.append(("donLV_adx20_stop3_H4_XAG", "XAGUSD", "H4", "build_regime", lv(stop=3.0), {}))
if __name__ == "__main__":
    run(J)
