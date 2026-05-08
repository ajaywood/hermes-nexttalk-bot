from __future__ import annotations
import httpx
import logging

log = logging.getLogger(__name__)

async def send_alert(bot_token: str, chat_id: str, text: str) -> bool:
    if not bot_token or not chat_id:
        log.warning("Telegram not configured - skipping alert")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
            return r.status_code == 200
    except Exception as e:
        log.error(f"Telegram alert failed: {e}")
        return False
