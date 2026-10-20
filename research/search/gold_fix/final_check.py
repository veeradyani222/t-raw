"""Re-score the named candidate builders with defaults (in-sample) + XAG cross-check."""
from research.prop import harness as H
from research.search.gold_fix import strategies as S
C = [("build_gold_lowvol_donchian", "H4"), ("build_gold_lowvol_donchian_fast", "H4"),
     ("build_bos_fixed_long", "M30"), ("build_bos_fixed", "M30"), ("build_gold_squeeze_adx", "H4")]
for fn, tf in C:
    for sym in ["XAUUSD"]:
        df = H.load(sym, tf, split="is")
        s = H.score(df, getattr(S, fn)(df), name=fn)
        h = s["headline"]
        print(H.summary_line(s), "| unfinished", h.get("challenge_unfinished"), "worst_month", round(h["worst_month"]))
