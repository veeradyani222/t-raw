from trader import multi_live


def test_each_account_gets_its_own_state_file():
    a, b = multi_live.state_path_for(114379496), multi_live.state_path_for(53122592)
    assert a != b and a.parent == b.parent == multi_live.STATE_PATH.parent
    assert a.name == "multi_state_114379496.json"


def test_account_change_exit_is_a_clean_exit():
    e = multi_live.AccountChanged(0)
    assert isinstance(e, SystemExit) and e.code == 0
