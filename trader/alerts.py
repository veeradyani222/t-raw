"""Telegram alerts. Degrades to log-only when no token is configured."""
import logging

import requests

from .config import Config

log = logging.getLogger("trader")


def send_alert(cfg: Config, text: str) -> None:
    log.info("ALERT: %s", text)
    if not cfg.telegram_token or not cfg.telegram_chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{cfg.telegram_token}/sendMessage",
            json={"chat_id": cfg.telegram_chat_id, "text": text},
            timeout=10,
        ).raise_for_status()
    except requests.RequestException as exc:
        log.error("telegram alert failed: %s", exc)
