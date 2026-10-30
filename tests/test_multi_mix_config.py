"""Loading another mix (MULTI_MIX_PATH), broker-specific symbol names,
the skip list, the conversion pairs the round-3 symbols need and the cost
patches the judge applied. No MT5, no data/."""
import json
import logging

import pandas as pd
import pytest

from research.prop import harness as H
from trader import multi
from trader.multi import StrategySpec

ROUND3 = [multi.ROOT / "docs" / "board" / f"portfolio-round3-{w}.json" for w in ("2y", "3y", "5y")]


# ----------------------------------------------------------------- mix path
def test_mix_path_defaults_to_the_66(monkeypatch):
    monkeypatch.delenv("MULTI_MIX_PATH", raising=False)
    assert multi.mix_path() == multi.MIX_PATH
    assert multi.MIX_PATH.name == "portfolio-lp300-66.json"


def test_mix_path_env_relative_to_repo_and_absolute(monkeypatch, tmp_path):
    monkeypatch.setenv("MULTI_MIX_PATH", "docs/board/portfolio-round3-2y.json")
    assert multi.mix_path() == multi.ROOT / "docs" / "board" / "portfolio-round3-2y.json"
    p = tmp_path / "mix.json"
    monkeypatch.setenv("MULTI_MIX_PATH", str(p))
    assert multi.mix_path() == p
    monkeypatch.setenv("MULTI_MIX_PATH", "   ")
    assert multi.mix_path() == multi.MIX_PATH


def test_load_mix_honours_the_env(monkeypatch):
    monkeypatch.setenv("MULTI_MIX_PATH", "docs/board/portfolio-round3-3y.json")
    specs = multi.load_mix()
    assert len(specs) == 62 and specs[0].idx == 0 and specs[-1].idx == 61
    monkeypatch.delenv("MULTI_MIX_PATH")
    assert len(multi.load_mix()) == 66


@pytest.mark.parametrize("path", ROUND3, ids=[p.stem for p in ROUND3])
def test_round3_mix_files_load_and_every_builder_imports(path):
    specs = multi.load_mix(path)
    assert len(specs) >= 50
    for s in specs:
        assert callable(s.builder()), s.name
        assert s.tf in multi.TF_MINUTES and 0 < s.risk <= 0.05 and s.symbol == s.symbol.upper()
    assert len({s.magic for s in specs}) == len(specs)


# ----------------------------------------------------------------- symbol map
def test_symbol_map_merges_the_matching_server_section(tmp_path):
    p = tmp_path / "symbols.json"
    p.write_text(json.dumps({
        "_comment": "x",
        "map": {"DE40": "DE40", "_note": "ignored"},
        "servers": {"ICMarketsSC": {"JPN225": "JP225", "_why": "ignored"},
                    "FundedNext": {"DE40": "GER40"}, "_Other": {"DE40": "DAX"}},
    }))
    assert multi.load_symbol_map(p) == {"DE40": "DE40"}
    assert multi.load_symbol_map(p, server="ICMarketsSC-Demo") == {"DE40": "DE40", "JPN225": "JP225"}
    assert multi.load_symbol_map(p, server="icmarketssc-live") == {"DE40": "DE40", "JPN225": "JP225"}
    assert multi.load_symbol_map(p, server="FundedNext-Server") == {"DE40": "GER40"}
    assert multi.load_symbol_map(p, server="MetaQuotes-Demo") == {"DE40": "DE40"}
    assert multi.load_symbol_map(tmp_path / "missing.json", server="ICMarketsSC-Demo") == {}


def test_repo_symbol_map_resolves_every_round3_symbol_on_ic():
    m = multi.load_symbol_map(server="ICMarketsSC-Demo")
    assert "_COMMENT" not in m and "_FUNDEDNEXT" not in m
    syms = {s.symbol for p in ROUND3 for s in multi.load_mix(p)}
    for s in syms:
        assert m.get(s, s), s           # a name, never empty
    # the research bars/specs for these came from IC under these exact names: no rename
    assert m.get("FRA40", "FRA40") == "FRA40" and m.get("JPN225", "JPN225") == "JPN225"


# ----------------------------------------------------------------- skip list
def test_skip_list_matches_module_fn_and_optional_symbol_tf(caplog):
    specs = [StrategySpec(0, "m.a", "build_x", {}, "XAUUSD", "H1", 0.01),
             StrategySpec(1, "m.a", "build_x", {}, "XAGUSD", "H1", 0.01),
             StrategySpec(2, "m.a", "build_y", {}, "XAUUSD", "H4", 0.01),
             StrategySpec(3, "m.b", "build_x", {}, "XAUUSD", "H1", 0.01)]
    skip = [{"module": "m.a", "fn": "build_x", "symbol": "xauusd", "reason": "needs silver"},
            {"module": "m.a", "fn": "build_y", "tf": "D1", "reason": "daily only"}]
    with caplog.at_level(logging.WARNING, logger="trader"):
        out = multi.skip_reasons(specs, skip)
    assert out == {0: "skip list: needs silver"}
    assert "SKIPPED" in caplog.text and "#00 x XAUUSD H1" in caplog.text


def test_repo_skip_list_names_only_cross_symbol_strategies_and_they_exist():
    skip = multi.load_skip_list()
    assert {e["fn"] for e in skip} == {"build_ratio_z", "build_spread_reversion"}
    for e in skip:
        assert e["reason"]
    hit = set()
    for p in ROUND3:
        for idx, why in multi.skip_reasons(multi.load_mix(p), skip).items():
            hit.add(why)
    assert len(hit) == 2, "every skip entry must still match a strategy in some mix"
    assert multi.load_skip_list(multi.ROOT / "config" / "nope.json") == []


def test_runner_never_trades_a_disabled_strategy(tmp_path):
    class Mkt:
        def rates(self, *a):
            raise AssertionError("a disabled strategy must not fetch bars")
        def tick_time(self, s):
            return None
        def account(self):
            return 10_000.0, 10_000.0
        def positions(self):
            return []
        def realized_since(self, t):
            return 0.0
    specs = multi.load_mix(ROUND3[0])[:3]
    r = multi.MultiRunner(Mkt(), specs, {}, disabled={s.idx: "skip list: test" for s in specs},
                          state_path=tmp_path / "s.json")
    r.warmup()
    assert r.poll() == [] and r.active_specs() == []
    assert any("disabled: 3" in ln for ln in r.status_lines())


# ----------------------------------------------------------------- conversion pairs
def test_round3_profit_currencies_all_have_a_conversion_pair():
    for p in ROUND3:
        for s in multi.load_mix(p):
            multi.conv_pair_for(s.symbol)       # raises KeyError when a currency is unknown
    assert multi.conv_pair_for("AUS200") == ("AUDUSD", False)
    assert multi.conv_pair_for("EURNOK") == ("USDNOK", True)
    assert multi.conv_pair_for("USDMXN") == ("USDMXN", True)
    assert multi.conv_pair_for("USDCNH") == ("USDCNH", True)
    assert multi.conv_pair_for("JPN225") == ("USDJPY", True)
    assert multi.conv_pair_for("BTCUSD") is None


def test_unknown_profit_currency_is_a_loud_error(monkeypatch):
    monkeypatch.setattr(multi, "_SPECS", {"FOO": {"profit_ccy": "XXX"}})
    with pytest.raises(KeyError, match="XXX"):
        multi.conv_pair_for("FOO")


def test_conv_symbols_lists_quote_only_pairs_per_user():
    specs = [StrategySpec(0, "m", "f", {}, "AUS200", "D1", 0.01), StrategySpec(1, "m", "f", {}, "USDMXN", "D1", 0.01),
             StrategySpec(2, "m", "f", {}, "XAUUSD", "H1", 0.01), StrategySpec(3, "m", "f", {}, "EURJPY", "H1", 0.01),
             StrategySpec(4, "m", "f", {}, "USDJPY", "H1", 0.01)]
    assert multi.conv_symbols(specs) == {"AUDUSD": ["AUS200"], "USDJPY": ["EURJPY"]}
    # USDMXN and USDJPY convert with their own close: no second symbol to fetch


def test_fetch_window_converts_usdmxn_with_its_own_close(tmp_path):
    t = pd.date_range("2026-11-02", periods=5, freq="D")
    df = pd.DataFrame(dict(time=t, open=17.5, high=17.6, low=17.4, close=[17.0, 17.5, 18.0, 17.5, 17.0],
                           tick_volume=1, spread=30))

    class Mkt:
        calls = []
        def rates(self, symbol, tf, count):
            self.calls.append(symbol)
            return df.copy()
    spec = StrategySpec(0, "m", "f", {}, "USDMXN", "D1", 0.01)
    r = multi.MultiRunner(Mkt(), [spec], {}, state_path=None, window=5)
    w = r.fetch_window("USDMXN", "D1")
    assert Mkt.calls == ["USDMXN"]
    assert list((1.0 / w["close"]).round(6)) == list(w["conv"].round(6))


# ----------------------------------------------------------------- cost patches / sizing
def test_research_patches_applied_once_and_leave_simulate_alone():
    before = H.simulate
    multi.apply_research_patches()
    multi.apply_research_patches()
    assert H.simulate is before
    assert {"BTCUSD", "XRPUSD", "XTIUSD", "XNGUSD", "AUS200", "JPN225", "CHINA50", "FRA40", "XPDUSD"} <= H.INDICES
    assert H.SPREAD_FLOOR["AUS200"] == 2.0 and H.SPREAD_FLOOR["EURNOK"] == 0.0055 and H.SPREAD_FLOOR["XTIUSD"] == 0.04
    assert H._pip("XPDUSD") == 0.1 and H._pip("XTIUSD") == 0.01 and H._pip("BTCUSD") == 2.5
    assert H._pip("XAUUSD") == 0.1 and H.SPREAD_FLOOR["XAUUSD"] == 0.30       # the originals untouched


def test_xrpusd_is_fundable_despite_its_100_lot_minimum():
    multi.apply_research_patches()
    sz = multi.size_trade("XRPUSD", "long", 0.5500, 0.5450, 0.5600, 40.0, 1.0, 0.01)
    assert sz is not None and sz["lots"] >= 100 and sz["lots"] % 0.01 < 1e-6
    assert abs(sz["risk_usd"] - 100.0) < 1.0
    # the 50-lot cap still holds elsewhere
    assert multi.size_trade("US500", "long", 5000.0, 4999.9, None, 1.0, 1.0, 0.02)["lots"] == 50.0


def test_crypto_sizing_reserves_no_commission():
    multi.apply_research_patches()
    sz = multi.size_trade("BTCUSD", "long", 60_000.0, 55_000.0, None, 2500.0, 1.0, 0.01)
    entry = 60_000.0 + 25.0 + 0.25                # floor 25 = bar spread 2500 pts x 0.01; slip 0.1 x pip 2.5
    assert abs(sz["entry_est"] - entry) < 1e-9
    assert abs(sz["loss_per_lot"] - ((entry - 55_000.0) + 0.25) * 1.0) < 1e-9      # no $14 commission
