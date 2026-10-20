from research.search.gold_fix.runner import run
G = "XAUUSD"
J = []
def d(name, sym, tf, bp, **kw):
    J.append((name, sym, tf, "build_regime", {"base": "build_donchian", "base_params": bp, **kw}, {}))
B = {"n_entry": 20, "n_exit": 10}
for am in [0.3, 0.4, 0.6, 0.7]:
    d(f"donch20_10_atrpmax{am}_H4", G, "H4", B, atrp_max=am, atrp_window=500)
for w in [250, 1000, 2000]:
    d(f"donch20_10_atrpmax0.5_w{w}_H4", G, "H4", B, atrp_max=0.5, atrp_window=w)
for ne, nx in [(15, 10), (30, 10), (20, 15), (40, 15), (55, 20)]:
    d(f"donch{ne}_{nx}_atrpmax0.5_H4", G, "H4", {"n_entry": ne, "n_exit": nx}, atrp_max=0.5, atrp_window=500)
d("donch20_10_atrpmax0.5_adx20_H4", G, "H4", B, atrp_max=0.5, atrp_window=500, adx_min=20)
d("donch20_10_atrpmax0.5_stop3_H4", G, "H4", {**B, "atr_stop": 3.0}, atrp_max=0.5, atrp_window=500)
d("donch20_10_atrpmax0.5_H4_XAG", "XAGUSD", "H4", B, atrp_max=0.5, atrp_window=500)
d("donch55_20_atrpmax0.5_H4_XAG", "XAGUSD", "H4", {"n_entry": 55, "n_exit": 20}, atrp_max=0.5, atrp_window=500)
d("donch80_40_atrpmax0.5_H1", G, "H1", {"n_entry": 80, "n_exit": 40, "atr_stop": 4.0}, atrp_max=0.5, atrp_window=2000)
d("donch20_10_atrpmax0.5_D1", G, "D1", B, atrp_max=0.5, atrp_window=250)
if __name__ == "__main__":
    run(J)
