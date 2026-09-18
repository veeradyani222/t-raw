"""Compare BOS price-action variants on equal footing. Untracked research tool.

Every variant is scored the SAME way: signals computed with the live rolling
2000-bar context, the sim started FLAT at the window start (live never inherits
a position), and allow_flip=True so the opposite-signal close matches
trader/engine.py. Getting any of those wrong silently flatters a variant.

Speed: simulate() walks every bar, so we slice the frame to WARMUP bars before
the window start rather than replaying from 2017. WARMUP > lookback means the
trailing 2000-bar context is complete for every scored bar, so signals are
identical to the full-history run — verified by `python bos_variants.py base`
reproducing the known +6296 two-year baseline.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("WF_SYM", "XAUUSD")

import pandas as pd

import wf_search as wf
from bos_backtest import load_vol, make_bos_signal

BASE = dict(swing_window=2, cmf_n=20, cmf_min=0.0, trend_ma=0, tp_mode="structure",
            tp_r=3.0, tp_min_r=1.0, use_cmf=True, lookback=2000)
RAILS_ON = dict(risk=0.01, start_equity=10_000.0, loss_baseline=10_000.0,
                daily_halt=0.03, total_halt=0.06)
RAILS_OFF = dict(risk=0.01, start_equity=10_000.0)
WARMUP = 3000
KILL = 9_400.0

_DF = None


def frame():
    global _DF
    if _DF is None:
        _DF = load_vol("M30", start="2017-01-01", end="2100-01-01")
    return _DF


def run(start: str, rails: bool = True, risk: float = 0.01, **overrides) -> dict:
    """Score one variant over one window."""
    df = frame()
    full_i = int(df.index[df["time"] >= pd.Timestamp(start)][0])
    lo = max(0, full_i - WARMUP)
    sl = df.iloc[lo:].reset_index(drop=True)
    di = full_i - lo

    cfg = {**BASE, **overrides}
    raw = make_bos_signal(sl, **cfg)
    rail = {**(RAILS_ON if rails else RAILS_OFF), "risk": risk}
    log = wf.simulate(sl, lambda f, i: raw(f, i) if i >= di else None,
                      allow_flip=True, **rail)["trade_log"]
    n = len(log)
    if not n:
        return dict(trades=0, net=0.0, win=0.0, dd=0.0, final=10_000.0, blown=False)
    eq = 10_000 + log["profit"].cumsum()
    return dict(trades=n, net=float(log["profit"].sum()),
                win=float((log["r_multiple"] > 0).mean() * 100),
                dd=float((eq - eq.cummax()).min()), final=float(eq.iloc[-1]),
                low=float(eq.min()), blown=bool(eq.iloc[-1] < KILL))


def show(label: str, r: dict, ref: dict | None = None) -> None:
    delta = ""
    if ref and ref["net"]:
        delta = f"{(r['net'] - ref['net']) / abs(ref['net']) * 100:>+7.0f}%"
    print(f"{label:<34}{r['trades']:>6}{r['win']:>7.0f}%{r['net']:>+11.0f}"
          f"{r['dd']:>+10.0f}{delta:>9}  {'BLOWN' if r['blown'] else ''}")


HDR = f"{'variant':<34}{'trades':>6}{'win':>8}{'net $':>11}{'maxDD':>10}{'vs base':>9}"

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "screen"
    START = "2024-09-04"
    if what == "base":
        print(HDR); print("-" * len(HDR))
        show("BASE rails ON", run(START, True))
        show("BASE rails OFF", run(START, False))

    if what == "screen":
        # Rails OFF: a permanent halt truncates a run and would hide how good a
        # variant actually is. Rails come back for the finalists.
        base = run(START, False)
        print(f"2 years from {START}, rails OFF (strategy quality only)")
        print(HDR); print("-" * len(HDR))
        show("BASE (swing 2, no trend MA)", base, base)
        for ma in (50, 100, 200):
            show(f"trend_ma={ma}", run(START, False, trend_ma=ma), base)
        for sw in (3, 4, 5):
            show(f"swing_window={sw}", run(START, False, swing_window=sw), base)

    if what == "robust":
        # The decisive test: does a variant hold up from ANY start, or did it
        # win one lucky window? Rails ON, because survival is the real metric.
        cands = [("BASE", {}), ("trend_ma=200", dict(trend_ma=200)),
                 ("swing_window=4", dict(swing_window=4)),
                 ("swing_window=5", dict(swing_window=5)),
                 ("sw=4 + ma=200", dict(swing_window=4, trend_ma=200)),
                 ("sw=5 + ma=200", dict(swing_window=5, trend_ma=200))]
        starts = [f"{y}-{m:02d}-01" for y, m in
                  [(2024, 9), (2024, 11), (2025, 1), (2025, 3), (2025, 5),
                   (2025, 7), (2025, 9), (2025, 11), (2026, 1), (2026, 3)]]
        print("net $ by start date, 1% risk, LIVE RAILS ON (! = blown, permanent halt)")
        head = f"{'variant':<16}" + "".join(f"{s[2:7]:>9}" for s in starts) + f"{'blown':>7}{'mean':>9}"
        print(head); print("-" * len(head))
        for name, ov in cands:
            nets, blown = [], 0
            for st in starts:
                r = run(st, True, **ov)
                nets.append(r["net"])
                if r["blown"]:
                    blown += 1
            cells = "".join(f"{n:>+8.0f}{'!' if n < -580 else ' '}" for n in nets)
            print(f"{name:<16}{cells}{blown:>6}/10{sum(nets)/len(nets):>+9.0f}")

    if what == "confirm":
        starts = [f"{y}-{m:02d}-01" for y, m in
                  [(2024, 9), (2024, 11), (2025, 1), (2025, 3), (2025, 5),
                   (2025, 7), (2025, 9), (2025, 11), (2026, 1), (2026, 3)]]

        def sweep(name, risk=0.01, **ov):
            nets, dds, blown = [], [], 0
            for st in starts:
                r = run(st, True, risk=risk, **ov)
                nets.append(r["net"]); dds.append(r["dd"]); blown += r["blown"]
            print(f"{name:<26}{blown:>3}/10 blown {sum(nets)/len(nets):>+9.0f} mean"
                  f" {min(nets):>+9.0f} worst {min(dds):>+9.0f} worstDD")

        print("A) is swing_window=4 real, or a lone spike? (all with trend_ma=200)")
        for sw in (2, 3, 4, 5, 6):
            sweep(f"   swing_window={sw}", swing_window=sw, trend_ma=200)
        print()
        print("B) ma=200 cuts drawdown - can that be spent on SIZE?")
        for risk in (0.01, 0.015, 0.02, 0.025):
            sweep(f"   risk={risk*100:.1f}% + ma=200", risk=risk, trend_ma=200)

    if what == "oos":
        # TRUE out-of-sample: every start below predates the 2024-09..2026-03
        # window the variants were screened on. If the filter only works on the
        # period it was chosen from, this is where it falls over.
        starts = [f"{y}-{m:02d}-01" for y in (2018, 2019, 2020, 2021, 2022, 2023)
                  for m in (1, 7)]

        def sweep(name, **ov):
            nets, dds, blown = [], [], 0
            for st in starts:
                r = run(st, True, **ov)
                nets.append(r["net"]); dds.append(r["dd"]); blown += r["blown"]
            print(f"{name:<26}{blown:>3}/{len(starts)} blown {sum(nets)/len(nets):>+9.0f} mean"
                  f" {min(nets):>+9.0f} worst {min(dds):>+9.0f} worstDD")

        print(f"OUT OF SAMPLE: {len(starts)} starts, 2018-2023, 1% risk, rails ON")
        sweep("   BASE")
        sweep("   trend_ma=200", trend_ma=200)
        sweep("   sw=4 + ma=200", swing_window=4, trend_ma=200)

    if what == "oos2":
        # Same out-of-sample idea, but every start now has a full WARMUP of
        # prior bars (the cache begins 2018-02-22, so 2018-01 was degenerate).
        starts = ["2018-09-01", "2019-01-01", "2019-07-01", "2020-01-01",
                  "2020-07-01", "2021-01-01", "2021-07-01", "2022-01-01",
                  "2022-07-01", "2023-01-01", "2023-07-01", "2024-01-01"]
        df = frame()
        print(f"data begins {df['time'].min()}; warmup needed {WARMUP} bars")
        for name, ov in [("BASE", {}), ("trend_ma=200", dict(trend_ma=200)),
                         ("sw=4 + ma=200", dict(swing_window=4, trend_ma=200))]:
            nets, blown = [], 0
            for st in starts:
                r = run(st, True, **ov)
                nets.append(r["net"]); blown += r["blown"]
            cells = "".join(f"{n:>+8.0f}{'!' if n < -580 else ' '}" for n in nets)
            print(f"{name:<15}{cells} {blown:>2}/{len(starts)} blown "
                  f"{sum(nets)/len(nets):>+8.0f} mean")

    if what == "regime":
        # Rails OFF: does the EDGE exist pre-2024, or only the drawdown problem?
        years = [("2018-09-01", "2019-09-01"), ("2019-09-01", "2020-09-01"),
                 ("2020-09-01", "2021-09-01"), ("2021-09-01", "2022-09-01"),
                 ("2022-09-01", "2023-09-01"), ("2023-09-01", "2024-09-01"),
                 ("2024-09-01", "2025-09-01"), ("2025-09-01", "2026-09-01")]
        print("One year at a time, rails OFF (pure edge), 1% risk, $10k reset each year")
        print(f"{'year from':<14}{'trades':>8}{'win':>7}{'BASE net':>11}{'ma=200 net':>13}")
        df = frame()
        for a, b in years:
            row = []
            for ov in ({}, dict(trend_ma=200)):
                full_i = int(df.index[df["time"] >= pd.Timestamp(a)][0])
                end_i = int(df.index[df["time"] >= pd.Timestamp(b)][0]) if pd.Timestamp(b) <= df["time"].max() else len(df)
                lo = max(0, full_i - WARMUP)
                sl = df.iloc[lo:end_i].reset_index(drop=True)
                di = full_i - lo
                raw = make_bos_signal(sl, **{**BASE, **ov})
                log = wf.simulate(sl, lambda f, i: raw(f, i) if i >= di else None,
                                  allow_flip=True, **RAILS_OFF)["trade_log"]
                row.append((len(log), float((log["r_multiple"] > 0).mean()*100) if len(log) else 0,
                            float(log["profit"].sum()) if len(log) else 0.0))
            print(f"{a[:7]:<14}{row[0][0]:>8}{row[0][1]:>6.0f}%{row[0][2]:>+11.0f}{row[1][2]:>+13.0f}")
