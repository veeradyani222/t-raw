"""Check build_mtf(H1 -> 4h donchian) ~= native H4 donchian score, plus causality."""
from research.prop import harness as H
from research.search.gold_fix import strategies as S
P = {"base": "build_regime", "base_params": {"base": "build_donchian", "base_params": {"n_entry": 20, "n_exit": 10},
     "atrp_max": 0.5, "atrp_window": 500, "adx_min": 20}}
d4 = H.load("XAUUSD", "H4", split="is")
print(H.summary_line(H.score(d4, S.build_regime(d4, **P["base_params"]), name="native_H4")))
for tf in ["H1", "M30"]:
    d = H.load("XAUUSD", tf, split="is")
    sig = S.build_mtf(d, rule="4h", base=P["base"], base_params=P["base_params"])
    print(H.summary_line(H.score(d, sig, name=f"mtf_on_{tf}")))
    k = len(d) // 2
    part = S.build_mtf(d.iloc[:k].reset_index(drop=True), rule="4h", base=P["base"], base_params=P["base_params"])
    bad = sum((a is None) != (b is None) or (a is not None and a.sl != b.sl) for a, b in zip(sig[k-2000:k], part[k-2000:k]))
    print("causal mismatches", bad)
