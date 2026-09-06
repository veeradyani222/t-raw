"""The exporter's shaping logic, without a terminal."""
from collections import namedtuple
from datetime import datetime, timezone

from ops.export_state import DEAL_FIELDS, deal_rows, status_payload, write_csv

Deal = namedtuple("Deal", "ticket order position_id time symbol type entry "
                          "volume price commission swap profit magic comment")
Pos = namedtuple("Pos", "ticket symbol type volume price_open sl tp profit")
Acct = namedtuple("Acct", "login server balance equity")


def a_deal(**kw):
    base = dict(ticket=1, order=2, position_id=3, time=1756600000, symbol="XAUUSD",
                type=1, entry=0, volume=0.02, price=4422.35, commission=0.0,
                swap=0.0, profit=-31.65, magic=0, comment="bos")
    base.update(kw)
    return Deal(**base)


def test_deal_rows_decodes_type_and_entry_to_words():
    row = deal_rows([a_deal(type=1, entry=1)])[0]
    assert row["type"] == "sell"
    assert row["entry"] == "out"


def test_deal_rows_renders_time_as_utc_string():
    row = deal_rows([a_deal(time=0)])[0]
    assert row["time"] == "1970-01-01 00:00:00"


def test_deal_rows_keeps_every_declared_field():
    assert set(deal_rows([a_deal()])[0]) == set(DEAL_FIELDS)


def test_deal_rows_handles_no_deals():
    assert deal_rows(None) == []
    assert deal_rows([]) == []


def test_status_payload_reports_account_and_open_positions():
    acct = Acct(login=111136986, server="MetaQuotes-Demo", balance=9561.12,
                equity=9510.05)
    pos = Pos(ticket=99, symbol="XAUUSD", type=1, volume=0.01,
              price_open=4384.06, sl=4476.49, tp=4310.73, profit=-51.07)
    out = status_payload(acct, [pos], "abc123",
                         datetime(2026, 9, 7, 23, 45, tzinfo=timezone.utc))
    assert out["commit"] == "abc123"
    assert out["account"]["login"] == 111136986
    assert out["exported_at"] == "2026-09-07 23:45:00 UTC"
    assert out["open_positions"][0]["type"] == "sell"
    assert out["open_positions"][0]["price_open"] == 4384.06


def test_status_payload_handles_flat_account():
    acct = Acct(login=1, server="s", balance=1.0, equity=1.0)
    assert status_payload(acct, [], "c", datetime.now(timezone.utc))["open_positions"] == []


def test_write_csv_round_trips(tmp_path):
    import csv
    path = tmp_path / "nested" / "deals.csv"
    write_csv(deal_rows([a_deal()]), path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["symbol"] == "XAUUSD"
    assert rows[0]["profit"] == "-31.65"
