"""Approximate a multi-strategy basket by summing per-strategy harness
curves at a common per-trade risk (summed worst-intrabar equity =
conservative). Info only - the harness judges one symbol at a time.
python -m research.search.published_research.portfolio"""
import pandas as pd
from research.prop import harness as H
from research.search.published_research import strategies as S

FX_FOMC = [("build_pre_fomc", s, dict(side=d, sl_datr=1.0)) for s, d in
           (("EURUSD", "long"), ("GBPUSD", "long"), ("AUDUSD", "long"), ("USDCHF", "short"))]
CAL = [("build_equity_calendar", "US30", dict(tom_days_before=0)),
       ("build_equity_calendar", "DE40", dict(tom_days_before=0)),
       ("build_equity_calendar", "US500", dict(tom_days_before=0)),
       ("build_gold_calendar", "XAUUSD", dict(tom_days_before=0))]


def basket_curve(legs, risk):
    curves = []
    for fn, sym, p in legs:
        df = H.load(sym, "H1", split="is")
        res = H.simulate(df, getattr(S, fn)(df, **p), risk=risk)
        c = res["curve"].set_index("time")[["worst", "close"]]
        curves.append(c[~c.index.duplicated()])
        del df, res
    idx = curves[0].index
    for c in curves[1:]:
        idx = idx.union(c.index)
    tot = sum(c.reindex(idx).ffill().fillna(0.0) for c in curves)
    tot = tot.reset_index().rename(columns={"index": "time"})
    return H._metrics(tot, pd.DataFrame({"profit": [0.0]}))


if __name__ == "__main__":
    for label, legs in (("FX pre-FOMC x4", FX_FOMC), ("calendar x4 (US30,DE40,US500,XAU)", CAL)):
        for r in (0.005, 0.0075, 0.01):
            m = basket_curve(legs, r)
            print(f"{label:<36} risk/leg {r:.4f} avg/mo {m['avg_month']:6.0f} maxDD {m['max_dd']:6.0f} "
                  f"worstDay {m['worst_day']:5.0f} green {m['green_months']:.2f} safe {m['safe']} "
                  f"chal {m['challenge_pass_rate']:.2f} ({m['challenge_median_days']} d)", flush=True)
