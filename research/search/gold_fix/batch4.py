from research.search.gold_fix.runner import run
G = "XAUUSD"
J = []
for ne in [15, 30, 40]:
    for nx in [10, 15]:
        J.append((f"donch{ne}_{nx}_H4", G, "H4", "build_donchian", {"n_entry": ne, "n_exit": nx}, {}))
J.append(("donch20_15_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 15}, {}))
J.append(("donch20_5_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 5}, {}))
for am in [18, 20, 22, 25]:
    J.append((f"donch20_10_adx{am}_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 10, "adx_min": am}, {}))
for st in [1.5, 3.0]:
    J.append((f"donch20_10_stop{st}_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 10, "atr_stop": st}, {}))
J.append(("donch20_10_ma200_H4", G, "H4", "build_donchian", {"n_entry": 20, "n_exit": 10, "ma_n": 200}, {}))
J.append(("donch80_40_H1", G, "H1", "build_donchian", {"n_entry": 80, "n_exit": 40}, {}))
J.append(("donch80_40_adx20_H1", G, "H1", "build_donchian", {"n_entry": 80, "n_exit": 40, "adx_min": 20}, {}))
J.append(("donch20_10_adx20_D1", G, "D1", "build_donchian", {"n_entry": 20, "n_exit": 10, "adx_min": 20}, {}))
J.append(("donch20_10_H4_XAG", "XAGUSD", "H4", "build_donchian", {"n_entry": 20, "n_exit": 10}, {}))
J.append(("donch20_10_adx20_H4_XAG", "XAGUSD", "H4", "build_donchian", {"n_entry": 20, "n_exit": 10, "adx_min": 20}, {}))
J.append(("donch55_20_H4_XAG", "XAGUSD", "H4", "build_donchian", {"n_entry": 55, "n_exit": 20}, {}))
if __name__ == "__main__":
    run(J)
