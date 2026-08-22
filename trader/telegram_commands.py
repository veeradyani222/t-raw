"""Inbound half of the Telegram integration: read commands the owner texts to
the bot, via getUpdates long-poll. (alerts.py is the outbound half.)

SECURITY: only messages from the configured chat_id are returned. The bot can
place orders, so it must never act on messages from anyone else.
"""
import logging

import requests

from .config import Config

log = logging.getLogger("trader")


def fetch_commands(cfg: Config, offset: int | None,
                   timeout: int = 10) -> tuple[list[str], int | None]:
    """Return (messages, new_offset).

    `messages` = the FULL text of each new message from the authorized chat, in
    arrival order (full text, not just the first word, so multi-word commands
    like `buy usdjpy` survive). `new_offset` must be passed back in on the next
    call so each Telegram update is consumed exactly once (it advances past EVERY
    update, including ignored ones, so foreign messages don't pile up).

    No-ops — returns ([], offset) — when Telegram isn't configured or the HTTP
    call fails, so a network blip never crashes the live loop.
    """
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        return [], offset

    params = {"timeout": 0}          # non-blocking; the live loop already polls
    if offset is not None:
        params["offset"] = offset
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{cfg.telegram_token}/getUpdates",
            params=params, timeout=timeout,
        )
        resp.raise_for_status()
        updates = resp.json().get("result", [])
    except (requests.RequestException, ValueError) as exc:
        log.error("telegram getUpdates failed: %s", exc)
        return [], offset

    commands, new_offset = [], offset
    for upd in updates:
        new_offset = upd["update_id"] + 1
        msg = upd.get("message") or upd.get("edited_message") or {}
        chat = msg.get("chat") or {}
        if str(chat.get("id")) != str(cfg.telegram_chat_id):
            continue                 # ignore everyone but the owner
        text = (msg.get("text") or "").strip()
        if not text:
            continue                 # skip stickers/photos/etc.
        commands.append(text)        # full text; the command parser splits it
    return commands, new_offset
