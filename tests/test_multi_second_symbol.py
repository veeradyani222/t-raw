"""The Brent-WTI spread strategy reads Brent closes through a module cache. Live, the
runner fills that cache from the broker's XBRUSD bars before every build; it must then
take the SAME trades as the harness does with the research Brent series.
Needs data/search/*.csv (git-ignored); skipped when absent."""
import os

import pandas as pd
import pytest

os.environ.setdefault("PROP_OOS", "1")

from research.prop import harness as H                     # noqa: E402
from research.search3.oil_gas import strategies as OIL     # noqa: E402
from trader import multi                                    # noqa: E402
from tests.fake_market import FakeMarket                    # noqa: E402
from tests.test_multi_parity import _replay_span            # noqa: E402

MIX24 = multi.ROOT / "docs" / "board" / "portfolio-round3-24.json"


def _spec():
    for s in multi.load_mix(MIX24):
        if s.fn == "build_spread_reversion":
            return s
    pytest.skip("no spread_reversion strategy in the 24 mix")


def test_second_symbol_table():
    s = _spec()
    assert multi.second_symbol(s) == "XBRUSD"
    assert all(multi.second_symbol(x) is None for x in multi.load_mix(MIX24) if x.fn != "build_spread_reversion")


def test_runner_feeds_live_brent_and_matches_harness(tmp_path):
    if not (H.DATA / "xbrusd-h4.csv").exists() or not (H.DATA / "xtiusd-h4.csv").exists():
        pytest.skip("cached research bars (data/search) not present")
    spec = _spec()
    wti, brent = H.load("XTIUSD", spec.tf, split="all"), H.load("XBRUSD", spec.tf, split="all")
    # reference: the harness with the full research Brent series in the cache
    OIL._other_cache[("XBRUSD", spec.tf)] = brent[["time", "close"]].rename(columns={"close": "oc"})
    wti.attrs.update(symbol="XTIUSD", tf=spec.tf)
    ref = H.simulate(wti, spec.build(wti), risk=spec.risk)["trades"]
    ref = ref[ref.reason != "end"] if len(ref) else ref
    OIL._other_cache.clear()                     # the runner must fill it itself

    start, n_bars = _replay_span(wti, ref)
    mkt = FakeMarket({"XTIUSD": wti, "XBRUSD": brent}, spec.tf, start)
    runner = multi.MultiRunner(mkt, [spec], {}, state_path=tmp_path / "s.json", window=multi.WINDOW_BARS,
                               guard=multi.AccountGuard(scale_size=1.0))
    runner.warmup()
    runner.last_bar[(spec.symbol, spec.tf)] = mkt.now
    for _ in range(n_bars):
        mkt.advance()
        runner.poll()
    span_t0 = wti["time"].iloc[start + 1]
    want = ref[(ref.entry_time >= span_t0) & (ref.entry_time <= mkt.now)].reset_index(drop=True)
    got = pd.DataFrame([e for e in runner.events if e["kind"] == "open"])
    assert len(want) >= 1 and len(got) == len(want), f"runner {len(got)} trades vs harness {len(want)}"
    for k in range(len(want)):
        assert pd.Timestamp(got.iloc[k]["time"]) == pd.Timestamp(want.iloc[k]["entry_time"])
        assert got.iloc[k]["side"] == want.iloc[k]["side"]
        assert abs(got.iloc[k]["lots"] - want.iloc[k]["lots"]) < 1e-9
    # the cache now holds the broker's (window-length) Brent bars, not research data
    assert len(OIL._other_cache[("XBRUSD", spec.tf)]) <= multi.WINDOW_BARS
