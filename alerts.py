"""
Alert delivery utilities (currently Telegram only).
"""

from __future__ import annotations

import logging
from typing import Final

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

LOGGER = logging.getLogger(__name__)


def send_alert(message: str) -> None:
    """
    Send a text message to the configured Telegram chat.

    Requires a valid TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.py.
    """
    if TELEGRAM_BOT_TOKEN.startswith("PASTE_") or TELEGRAM_CHAT_ID.startswith("PASTE_"):
        LOGGER.warning("Telegram credentials not configured; skipping alert:\n%s", message)
        return

    url: Final[str] = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        details = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            # Telegram typically returns JSON with a helpful "description"
            details = f" status={resp.status_code} body={resp.text!r}"
        LOGGER.error("Failed to send Telegram alert: %s%s", exc, details)

