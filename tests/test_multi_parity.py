"""Parity: the live runner's rolling-window path must take the SAME trades
as research.prop.harness.simulate on the same cached bars - same entry bars,
sides, stops and lots, and the same exits.

Strategies span M30/H1/H4/D1 and XAUUSD/DE40/EURJPY/US500/GBPJPY and are
taken straight from docs/board/portfolio-lp300-66.json by index.
Needs data/search/*.csv (git-ignored); skipped when absent.
"""
import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("PROP_OOS", "1")      # parity IS the verification stage

from research.prop import harness as H          # noqa: E402
from trader import multi                        # noqa: E402
from tests.fake_market import FakeMarket        # noqa: E402

WINDOW = multi.WINDOW_BARS

CASES = [  # (mix index, why)
    (20, "XAUUSD M30 bos + chandelier trail (manage)"),
    (2, "XAUUSD H1 bb_breakout, fixed sl/tp"),
    (27, "DE40 H1 session ORB, exit_hour + target"),
    (17, "EURJPY D1 connors_rsi2, manage close + JPY conversion"),
    (3, "US500 D1 rule ema_x, max_hold"),
    (11, "GBPJPY H4 rule rsi_rev trend, max_hold"),
    (4, "DE40 H1 prev_week, breakeven + trail"),
]


def _frames(spec):
    df = H.load(spec.symbol, spec.tf, split="all")
    frames = {spec.symbol: df}
    pair = multi.conv_pair_for(spec.symbol)
    if pair is not None:
        frames[pair[0]] = H.load(pair[0], spec.tf, split="all")
    return frames


def _replay_span(df, trades, n_trades=3, max_bars=900):
    """(start, n_bars): a replay covering the last `n_trades` harness trades,
    starting on a bar that no harness trade spans (so the runner starts flat
    like the harness), capped at `max_bars` bars."""
    times = df["time"].to_numpy()
    assert len(trades) >= n_trades, "strategy has too few harness trades"
    ent = np.searchsorted(times, trades.entry_time.to_numpy())
    ex = np.searchsorted(times, trades.exit_time.to_numpy())
    last = trades.iloc[-n_trades:]
    want = int(np.searchsorted(times, last.entry_time.iloc[0])) - 20
    want = max(want, int(ex.max()) - max_bars + 5, 0)
    for s in range(want, len(df) - 10):
        if not np.any((ent < s) & (ex >= s)):
            n = min(max_bars, len(df) - 1 - s, int(ex.max()) + 5 - s)
            return s, n
    pytest.skip("no flat bar found to start the replay")


@pytest.mark.parametrize("idx,why", CASES, ids=[c[1] for c in CASES])
def test_runner_matches_harness(idx, why, tmp_path):
    if not (H.DATA / "xauusd-h1.csv").exists():
        pytest.skip("cached research bars (data/search) not present")
    spec = multi.load_mix()[idx]
    frames = _frames(spec)
    df = frames[spec.symbol]
    sig_full = spec.build(df)
    ref = H.simulate(df, sig_full, risk=spec.risk)["trades"]
    ref = ref[ref.reason != "end"] if len(ref) else ref

    start, n_bars = _replay_span(df, ref)
    mkt = FakeMarket(frames, spec.tf, start)
    runner = multi.MultiRunner(mkt, [spec], {}, state_path=tmp_path / "s.json", window=WINDOW)
    runner.warmup()
    runner.last_bar[(spec.symbol, spec.tf)] = mkt.now       # bar `start` is "already seen"
    for _ in range(n_bars):
        mkt.advance()
        runner.poll()
    end_t = mkt.now

    span_t0 = df["time"].iloc[start + 1]
    want = ref[(ref.entry_time >= span_t0) & (ref.entry_time <= end_t)].reset_index(drop=True)
    got = pd.DataFrame([e for e in runner.events if e["kind"] == "open"])
    assert len(got) == len(want), f"{why}: runner opened {len(got)} trades, harness {len(want)}\n" \
                                  f"runner:\n{got}\nharness:\n{want}"
    assert len(want) >= 1, f"{why}: replay span had no harness trades"
    tol = float(H._spec().get(spec.symbol, {}).get("point", 0.01)) / 2   # half a broker point:
    # ATR/EMA warm-up on a 6000-bar window differs from full history by ~1e-7
    for k in range(len(want)):
        w, g = want.iloc[k], got.iloc[k]
        assert pd.Timestamp(g["time"]) == pd.Timestamp(w["entry_time"]), f"{why} trade {k}: entry bar"
        assert g["side"] == w["side"], f"{why} trade {k}: side"
        assert abs(g["sl"] - w["sl0"]) < tol, f"{why} trade {k}: stop {g['sl']} vs {w['sl0']}"
        assert abs(g["lots"] - w["lots"]) < 1e-9, f"{why} trade {k}: lots {g['lots']} vs {w['lots']}"
        assert abs(g["entry"] - w["entry"]) < 1e-9, f"{why} trade {k}: fill price"

    # exits: same bar and same kind of exit (stop/target by the broker, or
    # a time / manage / flip decision by the runner)
    closes = sorted(mkt.closes, key=lambda c: c["time"])
    closes = [c for c in closes if c["time"] <= end_t]
    want_x = want[want.exit_time <= end_t].reset_index(drop=True)
    assert len(closes) == len(want_x), f"{why}: {len(closes)} exits vs harness {len(want_x)}"
    for k in range(len(want_x)):
        w, g = want_x.iloc[k], closes[k]
        assert pd.Timestamp(g["time"]) == pd.Timestamp(w["exit_time"]), \
            f"{why} exit {k}: {g['time']} vs {w['exit_time']} ({g['reason']} vs {w['reason']})"
        assert g["reason"] == w["reason"], f"{why} exit {k}: reason {g['reason']} vs {w['reason']}"
        assert abs(g["pnl"] - w["profit"]) < 0.01, f"{why} exit {k}: pnl {g['pnl']} vs {w['profit']}"


def test_size_trade_matches_harness_block():
    # a long EURUSD at 1.10000 with a 30-pip stop, bar spread 10 points, conv 1
    sz = multi.size_trade("EURUSD", "long", 1.10000, 1.09700, None, 10.0, 1.0, 0.01)
    # harness: entry = c + max(0.00010, 10*1e-5) + 0.00001 ; loss/lot = (dist+slip)*100000 + 14
    entry = 1.10000 + 0.00010 + 0.00001
    loss = (abs(entry - 1.09700) + 0.00001) * 100000 + 14.0
    import math
    lots = min(round(math.floor(100.0 / loss / 0.01) * 0.01, 2), 50.0)
    assert sz["lots"] == lots and abs(sz["entry_est"] - entry) < 1e-12


def test_size_trade_skips_unfundable_and_invalid():
    assert multi.size_trade("XAUUSD", "long", 2000.0, 1500.0, None, 30, 1.0, 0.0025) is None
    assert multi.size_trade("XAUUSD", "long", 2000.0, 2001.0, None, 30, 1.0, 0.01) is None
    assert multi.size_trade("XAUUSD", "short", 2000.0, 1999.0, None, 30, 1.0, 0.01) is None
