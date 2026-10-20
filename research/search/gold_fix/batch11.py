from research.search.gold_fix.runner import run
def lv(ne=20, nx=7, tr=5.0, st=2.0):
    return {"base": "build_donchian", "base_params": {"n_entry": ne, "n_exit": nx, "atr_stop": st, "trail_atr": tr},
            "atrp_max": 0.5, "atrp_window": 500, "adx_min": 20}
J = []
for sym in ["USDJPY", "EURUSD", "GBPUSD", "AUDUSD"]:
    J.append((f"donLV20_x7_tr5_H4_{sym}", sym, "H4", "build_regime", lv(), {}))
J.append(("donLV20_x7_tr5_H4_spread2x", "XAUUSD", "H4", "build_regime", lv(), {"spread_mult": 2.0}))
J.append(("donLV15_x7_tr5_H4_spread2x", "XAUUSD", "H4", "build_regime", lv(ne=15), {"spread_mult": 2.0}))
J.append(("donLV20_x7_tr5_H4_noflip", "XAUUSD", "H4", "build_regime", lv(), {"allow_flip": False}))
J.append(("donLV20_x7_tr5_long_H4", "XAUUSD", "H4", "build_regime",
          {**lv(), "base_params": {**lv()["base_params"], "sides": ("long",)}}, {}))
J.append(("donLV20_x7_tr5_short_H4", "XAUUSD", "H4", "build_regime",
          {**lv(), "base_params": {**lv()["base_params"], "sides": ("short",)}}, {}))
J.append(("donLV20_x7_tr5_noadx_H4", "XAUUSD", "H4", "build_regime",
          {k: v for k, v in lv().items() if k != "adx_min"}, {}))
J.append(("donLV20_x7_tr5_noatrp_H4", "XAUUSD", "H4", "build_regime",
          {k: v for k, v in lv().items() if k not in ("atrp_max",)}, {}))
J.append(("donLV20_x7_tr5_H4_XAG", "XAGUSD", "H4", "build_regime", lv(), {}))
if __name__ == "__main__":
    run(J)
