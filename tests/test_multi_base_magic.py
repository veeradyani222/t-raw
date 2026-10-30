from trader import multi


def test_default_base_is_500000(monkeypatch):
    monkeypatch.delenv("MULTI_BASE_MAGIC", raising=False)
    assert multi.base_magic() == 500_000


def test_env_moves_the_whole_range(monkeypatch):
    monkeypatch.setenv("MULTI_BASE_MAGIC", "510000")
    assert multi.base_magic() == 510_000
    specs = multi.load_mix()
    assert specs[0].magic == 510_000 and specs[6].magic == 510_006
