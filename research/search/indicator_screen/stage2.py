"""Stage 2: real H.score for the screen's top clusters, with halves,
neighbouring parameters and sister symbols. Appends to verify_results.csv."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.search.indicator_screen.verify import run  # noqa: E402

JPY = ["GBPJPY", "EURJPY", "AUDJPY", "CADJPY", "NZDJPY", "CHFJPY", "USDJPY"]
IDX = ["US30", "US500", "DE40"]

PLAN = []
# 1 Keltner breakout, JPY crosses H4 (+ gold)
for s in JPY + ["XAUUSD"]:
    PLAN.append((s, "H4", "kelt_brk", False, {}))
for p in ({"n": 15}, {"n": 30}, {"k": 1.5}, {"k": 2.5}):
    PLAN.append(("GBPJPY", "H4", "kelt_brk", False, p))
PLAN.append(("GBPJPY", "H4", "kelt_brk", True, {}))
# 2 squeeze breakout + trend, JPY H4
for s in JPY + ["XAUUSD"]:
    PLAN.append((s, "H4", "squeeze_brk", True, {}))
for p in ({"q": 0.15}, {"q": 0.35}, {"n": 30}):
    PLAN.append(("GBPJPY", "H4", "squeeze_brk", True, p))
# 3 index trend H4: aroon + trend, ema_x + trend, dmi
for s in IDX:
    PLAN.append((s, "H4", "aroon_x", True, {}))
    PLAN.append((s, "H4", "ema_x", True, {}))
for p in ({"n": 20}, {"n": 35}):
    PLAN.append(("US30", "H4", "aroon_x", True, p))
for p in ({"f": 10, "s": 50}, {"f": 20, "s": 100}):
    PLAN.append(("US500", "H4", "ema_x", True, p))
# 4 gold H4 dmi
PLAN.append(("XAUUSD", "H4", "dmi_x", False, {}))
for p in ({"n": 10}, {"n": 20}, {"adx": 25}):
    PLAN.append(("XAUUSD", "H4", "dmi_x", False, p))
PLAN.append(("XAGUSD", "H4", "dmi_x", False, {}))
# 5 MFI reversal CHFJPY H4, AUDUSD keltner reversion
PLAN.append(("CHFJPY", "H4", "mfi_rev", False, {}))
PLAN.append(("CHFJPY", "H4", "mfi_rev", False, {"lo": 15}))
PLAN.append(("CHFJPY", "H4", "mfi_rev", False, {"lo": 25}))
PLAN.append(("AUDUSD", "H4", "kelt_rev", False, {}))
PLAN.append(("AUDUSD", "H4", "kelt_rev", False, {"k": 1.5}))
PLAN.append(("AUDUSD", "H4", "kelt_rev", False, {"k": 2.5}))
PLAN.append(("NZDUSD", "H4", "kelt_rev", False, {}))
# 6 D1 Donchian breakout (turtle-like) on JPY crosses + gold
for s in JPY + ["XAUUSD"]:
    PLAN.append((s, "D1", "don_brk", False, {}))
PLAN.append(("GBPJPY", "D1", "don_brk", False, {"n": 15}))
PLAN.append(("GBPJPY", "D1", "don_brk", False, {"n": 30}))

if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for sym, tf, rule, trend, p in PLAN:
        if only and only not in (sym, tf, rule):
            continue
        try:
            run(sym, tf, rule, trend, **p)
        except Exception as e:
            print("FAIL", sym, tf, rule, p, type(e).__name__, e, flush=True)
