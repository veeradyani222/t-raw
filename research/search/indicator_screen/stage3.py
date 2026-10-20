"""Stage 3 ("fix what fails"): (a) consensus trend vote rule on all symbols H4/D1
(quick 1% pass), (b) real H.score for the most consistent D1 rule (squeeze_brk+T)
on every symbol, (c) exit-variant check on the two least-bad H4 clusters."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research.prop import harness as H  # noqa: E402
from research.search.indicator_screen import strategies as S  # noqa: E402
from research.search.indicator_screen.screen import SYMS, quick  # noqa: E402
from research.search.indicator_screen.verify import run  # noqa: E402

OUT = Path(__file__).with_name("stage3_vote.csv")

if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "abc"
    if "a" in part:
        rows = []
        for sym in SYMS:
            if sym == "USTEC":
                continue
            for tf in ("H4", "D1"):
                df = H.load(sym, tf)
                for v in (4, 5, 6):
                    lg, sh = S.rule_events(df, "trend_vote", {"v": v})
                    for trend in (False, True):
                        r = quick(df, S.events_to_entries(df, lg, sh, trend=trend))
                        r.update(symbol=sym, tf=tf, rule=f"trend_vote v={v}", trend=trend)
                        rows.append(r)
            print(sym, flush=True)
        d = pd.DataFrame(rows); d.to_csv(OUT, index=False)
        d["both"] = (d.h1_avgmo > 0) & (d.h2_avgmo > 0)
        print(d.groupby(["tf", "rule", "trend"]).agg(pos=("net1", lambda x: (x > 0).mean()),
              both=("both", "mean"), med_pf=("pf", "median"), sum_net=("net1", "sum")).round(2))
        print(d.sort_values("avg_month_est", ascending=False).head(10)[
            ["symbol", "tf", "rule", "trend", "trades", "pf", "net1", "best_risk_est",
             "avg_month_est", "h1_avgmo", "h2_avgmo"]].round(2).to_string())
    if "b" in part:
        for sym in SYMS:
            if sym != "USTEC":
                run(sym, "D1", "squeeze_brk", True)
    if "c" in part:
        for hold, tp in ((96, 3.0), (48, 4.0), (96, 5.0)):
            run("GBPJPY", "H4", "kelt_brk", False, tag=f" hold={hold} tp={tp}", hold=hold, tp_atr=tp)
            run("US30", "H4", "aroon_x", True, tag=f" hold={hold} tp={tp}", hold=hold, tp_atr=tp)
        for sides in ("long", "short"):
            run("US30", "H4", "aroon_x", True, sides=sides)
            run("US500", "H4", "ema_x", True, sides=sides)
            run("GBPJPY", "H4", "kelt_brk", False, sides=sides)
