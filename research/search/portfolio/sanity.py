"""Check the combiner reproduces the verifier's single-strategy OOS numbers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import combine as C  # noqa: E402

b = C.Book(["de40_orb", "gold_bb", "gold_cal"], "oos")
for a in ({"de40_orb": 0.005}, {"gold_bb": 0.005}, {"gold_cal": 0.02}):
    m = b.full(a)
    print(a, round(m["net"], 2), round(m["max_dd"], 1), round(m["worst_day"], 1), m["trades"],
          m["challenge_pass"], round(m["max_open_risk"], 1))
print("expected: de40 1216.67/-743.8/-220.4/254 ; gold_bb 1181.03/-512.58/-133.81/129 ; gold_cal 2159.02/-391.39/-204.04/41")
