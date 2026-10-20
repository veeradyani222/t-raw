from research.search.gold_fix.runner import run
G = "XAUUSD"
J = []
for ne in [15, 20]:
    for nx in [5, 7, 10]:
        for tr in [None, 4.0, 5.0, 6.0]:
            for st in [2.0, 2.5]:
                bp = {"n_entry": ne, "n_exit": nx, "atr_stop": st}
                if tr:
                    bp["trail_atr"] = tr
                p = {"base": "build_donchian", "base_params": bp, "atrp_max": 0.5, "atrp_window": 500, "adx_min": 20}
                J.append((f"grid_donLV{ne}_x{nx}_tr{tr}_st{st}_H4", G, "H4", "build_regime", p, {}))
if __name__ == "__main__":
    run(J)
