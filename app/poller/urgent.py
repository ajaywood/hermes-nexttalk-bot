from __future__ import annotations
import json
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)
URGENT_STATE_FILE = Path("/data/state/urgent_state.json")

class UrgentModeManager:
    def __init__(self):
        self._state: dict = {}
        self.load()

    def load(self) -> None:
        if URGENT_STATE_FILE.exists():
            try:
                self._state = json.loads(URGENT_STATE_FILE.read_text())
            except Exception:
                self._state = {}

    def save(self) -> None:
        URGENT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            URGENT_STATE_FILE.write_text(json.dumps(self._state, indent=2))
        except Exception as e:
            log.error(f"Failed to save urgent state: {e}")

    def is_active(self, token: str) -> bool:
        return self._state.get(token, {}).get("active", False)

    def activate(self, token: str) -> None:
        now = time.time()
        self._state[token] = {"active": True, "activated_at": now, "last_user_msg_at": now}
        self.save()
        log.info(f"Urgent mode ACTIVATED for {token}")

    def deactivate(self, token: str, reason: str = "calm signal") -> None:
        self._state[token] = {"active": False, "activated_at": 0, "last_user_msg_at": 0}
        self.save()
        log.info(f"Urgent mode DEACTIVATED for {token} ({reason})")

    def update_last_message_time(self, token: str) -> None:
        if token in self._state and self._state[token].get("active"):
            self._state[token]["last_user_msg_at"] = time.time()
            self.save()

    def check_timeout(self, token: str, timeout_seconds: int) -> bool:
        s = self._state.get(token, {})
        if not s.get("active"):
            return False
        last = s.get("last_user_msg_at", time.time())
        return (time.time() - last) > timeout_seconds

    def get_effective_interval(self, token: str, default_interval: int, urgent_interval: int) -> int:
        if self.is_active(token):
            return urgent_interval
        return default_interval
