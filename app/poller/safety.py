from __future__ import annotations
import logging
from .telegram import send_alert

log = logging.getLogger(__name__)

async def check_and_alert(user_msgs: list[dict], room_name: str, keywords: list[str], bot_token: str, chat_id: str) -> bool:
    for m in user_msgs:
        text = m.get("message", "").lower()
        for kw in keywords:
            if kw in text:
                actor = m.get("actorDisplayName", "Someone")
                alert = (
                    f"SAFETY ALERT - {room_name}\n\n"
                    f"{actor} has said something that may need your gentle attention.\n\n"
                    f"Please reach out to them soon - calmly and without pressure.\n\n"
                    f"This is a confidential flag from Hermes. No details shared here."
                )
                await send_alert(bot_token, chat_id, alert)
                log.warning(f"[{room_name}] Safety alert sent (keyword: '{kw}')")
                return True
    return False
