from trader import multi


def test_default_base_is_500000(monkeypatch):
    monkeypatch.delenv("MULTI_BASE_MAGIC", raising=False)
    assert multi.base_magic() == 500_000


def test_env_moves_the_whole_range(monkeypatch):
    monkeypatch.setenv("MULTI_BASE_MAGIC", "510000")
    assert multi.base_magic() == 510_000
    specs = multi.load_mix()
    assert specs[0].magic == 510_000 and specs[6].magic == 510_006


def test_max_risk_caps_only_the_big_ones(monkeypatch):
    monkeypatch.setenv("MULTI_MAX_RISK", "0.0275")
    raw = __import__("json").load(open(multi.ROOT / "docs/board/portfolio-round3-2y.json"))["mix"]
    specs = multi.load_mix(multi.ROOT / "docs/board/portfolio-round3-2y.json")
    assert max(s.risk for s in specs) == 0.0275
    changed = [s for s, m in zip(specs, raw) if s.risk != m["risk"]]
    assert len(changed) == 2 and all(m["risk"] == 0.03 for s, m in zip(specs, raw) if s.risk != m["risk"])


def test_no_cap_by_default(monkeypatch):
    monkeypatch.delenv("MULTI_MAX_RISK", raising=False)
    assert multi.max_risk() == float("inf")
