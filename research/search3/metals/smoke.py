"""Smoke + causality check of every builder on one df (default XAUUSD H1)."""
import random, sys, time
from research.search3.metals import runner  # patches harness
from research.prop import harness as H
from research.search3.metals import strategies as S
import numpy as np

sym = sys.argv[1] if len(sys.argv) > 1 else "XAUUSD"
tf = sys.argv[2] if len(sys.argv) > 2 else "H1"
df = H.load(sym, tf, split="oos")
print(sym, tf, len(df), "bars; bad ticks fixed:", runner.BAD)

CASES = [
    ("build_gap_fade", {}),
    ("build_gap_fade", dict(mode="follow", tp="r:1.5")),
    ("build_asia_dip", {}),
    ("build_d1_reversal", {}),
    ("build_wopen_retest", {}),
    ("build_channel_pt", {}),
    ("build_channel_pt", dict(trail_atr=2.0)),
    ("build_round_level", dict(step=100.0, stop_frac=0.2)),
    ("build_asia_break", {}),
    ("build_asia_break", dict(a0=1, a1=10, tp="pdhl", exit_hour=22)),
    ("build_asia_fade", {}),
    ("build_pd_sweep", {}),
    ("build_pd_sweep", dict(level="pw", tp="r:1.5")),
    ("build_pd_break", {}),
    ("build_session_hold", {}),
    ("build_session_hold", dict(side="short", h_in=15, h_out=22, dows=(0, 1))),
    ("build_ratio_z", dict(other="XAGUSD")),
    ("build_lag_catchup", dict(leader="XAGUSD")),
    ("build_round_level", dict(step=50.0)),
    ("build_round_level", dict(step=50.0, mode="fade")),
    ("build_nr_break", {}),
    ("build_nr_break", dict(inside=True)),
    ("build_fix_fade", {}),
    ("build_fix_fade", dict(fix="am", mode="follow")),
    ("build_late_day", {}),
    ("build_gap_fade", {}),
    ("build_gap_fade", dict(mode="follow", tp="r:1.5")),
    ("build_asia_dip", {}),
    ("build_d1_reversal", {}),
    ("build_wopen_retest", {}),
    ("build_channel_pt", {}),
    ("build_channel_pt", dict(trail_atr=2.0)),
]


def same(a, b):
    if (a is None) != (b is None):
        return False
    if a is None:
        return True
    tp_eq = (a.tp is None and b.tp is None) or (a.tp is not None and b.tp is not None and abs(a.tp - b.tp) < 1e-9)
    return a.side == b.side and abs(a.sl - b.sl) < 1e-9 and tp_eq and a.max_hold == b.max_hold and a.exit_hour == b.exit_hour


random.seed(3)
for fn, p in CASES:
    t0 = time.time()
    full = getattr(S, fn)(df, **p)
    nsig = sum(1 for s in full if s is not None)
    assert len(full) == len(df)
    ks = sorted(random.sample(range(len(df) // 3, len(df) - 5), 3))
    diffs = 0
    for k in ks:
        part = df.iloc[:k].copy(); part.attrs.update(df.attrs)
        sub = getattr(S, fn)(part, **p)
        diffs += sum(1 for i in range(k) if not same(full[i], sub[i]))
    tb = time.time() - t0
    s = H.score(df, full, name=fn)
    print(f"{fn:<20} {str(p)[:50]:<52} sig {nsig:>5} causal_diffs {diffs}  build {tb:.1f}s score {time.time()-t0-tb:.1f}s  -> {H.summary_line(s)[40:]}")
