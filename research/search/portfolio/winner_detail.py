"""Details for the report: IS-only selection (honest pick), winner yearly split,
per-strategy trade counts, correlation of monthly P&L, skipped-for-min-lot."""
import sys
import json
import itertools
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import combine as C  # noqa: E402
from research.prop import harness as H  # noqa: E402

names = ["de40_orb", "gold_bb", "gold_cal"]
B = {s: C.Book(names, s) for s in ("is", "oos")}
levels = (0.0,) + tuple(H.RISKS)
best = None
for combo in itertools.product(levels, repeat=3):
    if not any(combo):
        continue
    a = dict(zip(names, combo))
    q = B["is"].quick(a)
    if q["safe"] and (best is None or q["net"] > best[1]["net"]):
        best = (a, q)
a_is = best[0]
out = {}
for label, a in (("is_selected", a_is),
                 ("winner", {"de40_orb": 0.0025, "gold_bb": 0.0025, "gold_cal": 0.02}),
                 ("runner_up_lower_risk", {"de40_orb": 0.0025, "gold_bb": 0.0025, "gold_cal": 0.0125})):
    fo, fi = B["oos"].full(a), B["is"].full(a)
    mo = pd.Series(fo["monthly"])
    yearly = mo.groupby(mo.index.str[:4]).sum().round(0).to_dict()
    mi = pd.Series(fi["monthly"])
    yearly_is = mi.groupby(mi.index.str[:4]).sum().round(0).to_dict()
    tr = B["oos"].trades(a)
    tr = tr[tr.entry_time >= H.OOS_START]
    per = tr.groupby("strategy")["profit"].agg(["count", "sum"]).round(0).to_dict("index")
    out[label] = dict(combo=C.fmt(a), oos={k: fo[k] for k in ("net", "avg_month", "green_months", "worst_month",
                      "max_dd", "worst_day", "trades", "challenge_pass", "challenge_fail", "challenge_attempts",
                      "challenge_unfinished", "challenge_median_days", "max_open_risk", "max_concurrent",
                      "cap_breach_events", "months")},
                      is_={k: fi[k] for k in ("net", "avg_month", "green_months", "max_dd", "worst_day", "trades",
                           "challenge_pass", "challenge_fail", "challenge_attempts", "challenge_median_days",
                           "max_open_risk", "cap_breach_events", "months")},
                      oos_yearly=yearly, is_yearly=yearly_is, oos_per_strategy=per)
# monthly correlation of the three survivors OOS at their winner risk
ms = {}
for n, r in (("de40_orb", 0.0025), ("gold_bb", 0.0025), ("gold_cal", 0.02)):
    ms[n] = pd.Series(B["oos"].full({n: r})["monthly"])
out["oos_monthly_corr"] = pd.DataFrame(ms).fillna(0).corr().round(2).to_dict()
print(json.dumps(out, indent=1, default=str))
with open(Path(__file__).parent / "winner_detail.json", "w") as f:
    json.dump(out, f, indent=1, default=str)
