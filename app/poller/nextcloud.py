from __future__ import annotations
import httpx
import logging

log = logging.getLogger(__name__)

class NextcloudClient:
    def __init__(self, url: str, user: str, password: str):
        self.base = url.rstrip("/")
        self.auth = (user, password)
        self.headers = {"OCS-APIRequest": "true", "Accept": "application/json"}

    async def get_new_messages(self, token: str, since_id: int = 0) -> list[dict]:
        """IMPORTANT: Do NOT use lastKnownMessageId - it returns OLDER messages. Always fetch latest and filter manually."""
        url = f"{self.base}/ocs/v2.php/apps/spreed/api/v4/chat/{token}?limit=50&lookIntoFuture=0"
        try:
            async with httpx.AsyncClient(auth=self.auth, headers=self.headers, timeout=30) as client:
                r = await client.get(url)
                r.raise_for_status()
                msgs = r.json().get("ocs", {}).get("data", [])
                return [m for m in msgs if not m.get("systemMessage") and m.get("id", 0) > since_id]
        except Exception as e:
            log.error(f"get_new_messages({token}): {e}")
            return []

    async def get_history(self, token: str, limit: int = 20) -> list[dict]:
        url = f"{self.base}/ocs/v2.php/apps/spreed/api/v4/chat/{token}?limit={limit}&lookIntoFuture=0"
        try:
            async with httpx.AsyncClient(auth=self.auth, headers=self.headers, timeout=30) as client:
                r = await client.get(url)
                r.raise_for_status()
                msgs = r.json().get("ocs", {}).get("data", [])
                return list(reversed([m for m in msgs if not m.get("systemMessage")]))
        except Exception as e:
            log.error(f"get_history({token}): {e}")
            return []

    async def send_message(self, token: str, message: str) -> bool:
        url = f"{self.base}/ocs/v2.php/apps/spreed/api/v4/chat/{token}"
        try:
            async with httpx.AsyncClient(auth=self.auth, timeout=30) as client:
                r = await client.post(url, data={"message": message}, headers={**self.headers, "Content-Type": "application/x-www-form-urlencoded"})
                return r.json().get("ocs", {}).get("meta", {}).get("statuscode") == 201
        except Exception as e:
            log.error(f"send_message({token}): {e}")
            return False

    async def get_rooms(self) -> list[dict]:
        url = f"{self.base}/ocs/v2.php/apps/spreed/api/v4/room"
        try:
            async with httpx.AsyncClient(auth=self.auth, headers=self.headers, timeout=30) as client:
                r = await client.get(url)
                r.raise_for_status()
                return r.json().get("ocs", {}).get("data", [])
        except Exception as e:
            log.error(f"get_rooms(): {e}")
            return []
