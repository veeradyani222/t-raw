from research.search.gold_fix.runner import run
J = []
for tf in ["M30", "H1", "H4"]:
    J.append((f"bos_base_{tf}", "XAUUSD", tf, "build_bos", {}, {}))
    J.append((f"bos_noflip_{tf}", "XAUUSD", tf, "build_bos", {}, {"allow_flip": False}))
    for mr in [2.0, 3.0]:
        J.append((f"bos_tpmin{mr}_{tf}", "XAUUSD", tf, "build_bos", {"tp_min_r": mr}, {}))
    for r in [2.0, 3.0]:
        J.append((f"bos_fixR{r}_{tf}", "XAUUSD", tf, "build_bos", {"tp_mode": "fixed", "tp_r": r}, {}))
    J.append((f"bos_atrp0.6_{tf}", "XAUUSD", tf, "build_bos", {"atrp_min": 0.6}, {}))
    J.append((f"bos_tpmin2_atrp0.6_{tf}", "XAUUSD", tf, "build_bos", {"tp_min_r": 2.0, "atrp_min": 0.6}, {}))
if __name__ == "__main__":
    run(J)
