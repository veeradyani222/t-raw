"""Telegram alerts. Degrades to log-only when no token is configured."""
import logging

import requests

from .config import Config

log = logging.getLogger("trader")


def send_alert(cfg: Config, text: str, reply_markup: dict | None = None) -> None:
    """Send a Telegram message. `reply_markup` (optional) attaches a keyboard —
    used to show the tappable command buttons so the owner doesn't type."""
    log.info("ALERT: %s", text)
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        return
    payload = {"chat_id": cfg.telegram_chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(
            f"https://api.telegram.org/bot{cfg.telegram_token}/sendMessage",
            json=payload,
            timeout=10,
        ).raise_for_status()
    except requests.RequestException as exc:
        log.error("telegram alert failed: %s", exc)
