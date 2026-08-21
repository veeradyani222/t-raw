"""Tests for trader.telegram_commands.fetch_commands — the inbound Telegram
listener. requests.get is monkeypatched, so no network is touched; we verify the
chat-id security filter, offset bookkeeping, and graceful degradation."""
import requests

from trader import telegram_commands
from trader.config import Config

CFG = Config(telegram_token="TESTTOKEN", telegram_chat_id="555")


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _updates(*items):
    return {"ok": True, "result": list(items)}


def _msg(update_id, chat_id, text):
    return {"update_id": update_id,
            "message": {"chat": {"id": chat_id}, "text": text}}


def test_returns_commands_from_the_authorized_chat(monkeypatch):
    payload = _updates(_msg(10, 555, "buy"), _msg(11, 555, "/Close please"))
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp(payload))
    cmds, offset = telegram_commands.fetch_commands(CFG, None)
    assert cmds == ["buy", "/Close"]      # first word only, order preserved
    assert offset == 12                   # max update_id + 1


def test_ignores_messages_from_other_chats_but_still_advances_offset(monkeypatch):
    payload = _updates(_msg(20, 999, "buy"), _msg(21, 555, "status"))
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp(payload))
    cmds, offset = telegram_commands.fetch_commands(CFG, None)
    assert cmds == ["status"]             # stranger's "buy" dropped
    assert offset == 22                   # advanced past BOTH so it won't repeat


def test_skips_non_text_messages(monkeypatch):
    payload = {"result": [{"update_id": 30,
                           "message": {"chat": {"id": 555}}}]}  # e.g. a sticker
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp(payload))
    cmds, offset = telegram_commands.fetch_commands(CFG, None)
    assert cmds == [] and offset == 31


def test_passes_offset_as_getUpdates_param(monkeypatch):
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen["params"] = params
        return FakeResp(_updates())

    monkeypatch.setattr(requests, "get", fake_get)
    telegram_commands.fetch_commands(CFG, 100)
    assert seen["params"].get("offset") == 100


def test_no_op_when_telegram_unconfigured(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("must not call the network when unconfigured")

    monkeypatch.setattr(requests, "get", explode)
    cmds, offset = telegram_commands.fetch_commands(Config(), 7)
    assert cmds == [] and offset == 7


def test_network_error_degrades_to_no_op(monkeypatch):
    def boom(*a, **k):
        raise requests.RequestException("down")

    monkeypatch.setattr(requests, "get", boom)
    cmds, offset = telegram_commands.fetch_commands(CFG, 42)
    assert cmds == [] and offset == 42    # keeps its place, no crash
