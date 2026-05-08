from __future__ import annotations
import asyncio
import json
import logging
import logging.handlers
import os
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, "/app")

from shared.config import get_config
from poller.nextcloud import NextcloudClient
from poller.claude import ClaudeClient
from poller.telegram import send_alert
from poller.safety import check_and_alert
from poller.urgent import UrgentModeManager
from poller.memory import load_memory, save_memory

HEARTBEAT_FILE = Path("/data/state/heartbeat")
PID_FILE = Path("/data/state/poller.pid")
POLL_STATE_FILE = Path("/data/state/poll_state.json")
LOG_FILE = Path("/data/logs/poller.log")

def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

log = logging.getLogger("poller")

def load_poll_state() -> dict:
    if POLL_STATE_FILE.exists():
        try:
            return json.loads(POLL_STATE_FILE.read_text())
        except Exception:
            pass
    return {}

def save_poll_state(state: dict) -> None:
    POLL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(mode="w", dir=POLL_STATE_FILE.parent, delete=False, suffix=".tmp")
    try:
        json.dump(state, tmp, indent=2)
        tmp.close()
        os.replace(tmp.name, POLL_STATE_FILE)
    except Exception as e:
        log.error(f"Failed to save poll state: {e}")
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

def format_messages(msgs: list[dict]) -> str:
    return "\n".join(
        f"{m.get('actorDisplayName', m.get('actorId', '?'))}: {m.get('message', '')}"
        for m in msgs
    )

async def process_room(token: str, room_cfg, poll_state: dict, nc: NextcloudClient, claude: ClaudeClient, urgent_mgr: UrgentModeManager, cfg) -> None:
    role = room_cfg.role.value
    room_name = room_cfg.name
    memory_file = room_cfg.memory_file
    since_id = poll_state.get(token, 0)

    new_msgs = await nc.get_new_messages(token, since_id)
    if not new_msgs:
        return

    max_id = max(m["id"] for m in new_msgs)
    poll_state[token] = max_id

    bot_user = cfg.nextcloud.user
    user_msgs = [m for m in new_msgs if m.get("actorId") != bot_user]
    if not user_msgs:
        return

    log.info(f"[{room_name}] {len(user_msgs)} new message(s)")

    if role in ("lilly", "james"):
        await check_and_alert(user_msgs, room_name, cfg.safety_keywords, cfg.telegram.bot_token, cfg.telegram.chat_id)

    if role == "family_mediator":
        has_aaron = any(m.get("actorId") == "awood" for m in user_msgs)
        unique_actors = set(m.get("actorId") for m in user_msgs)
        if not has_aaron and len(unique_actors) < 2:
            log.info(f"[{room_name}] Waiting for back-and-forth")
            return

    urgent = False
    if room_cfg.urgent_capable:
        trigger_words = cfg.polling.urgent_trigger_words
        calm_words = cfg.polling.urgent_calm_words
        timeout = cfg.polling.urgent_calm_timeout
        if urgent_mgr.is_active(token):
            for m in user_msgs:
                text = m.get("message", "").lower().strip()
                if any(w in text for w in calm_words):
                    urgent_mgr.deactivate(token, "calm signal")
                    await nc.send_message(token, "Glad you're feeling better. I'm still here whenever you need me.")
                    break
            if urgent_mgr.check_timeout(token, timeout):
                urgent_mgr.deactivate(token, "10 min silence")
                await nc.send_message(token, "Things seem calmer. Dropping back to normal - message me any time.")
            if urgent_mgr.is_active(token):
                urgent_mgr.update_last_message_time(token)
                urgent = True
        else:
            for m in user_msgs:
                text = m.get("message", "").lower().strip()
                if any(w in text for w in trigger_words):
                    urgent_mgr.activate(token)
                    urgent = True
                    break

    memory_content = load_memory(memory_file) if memory_file else ""
    new_ids = {m["id"] for m in new_msgs}
    history_msgs = [m for m in await nc.get_history(token, cfg.polling.history_limit) if m["id"] not in new_ids]
    history_context = format_messages(history_msgs)
    new_context = format_messages(list(reversed(new_msgs)))
    model = room_cfg.model or cfg.anthropic.default_model

    reply = await claude.respond(new_context, role, room_name, memory_content, history_context, urgent, model)
    if not reply:
        return

    await nc.send_message(token, reply)

    if memory_file and memory_content:
        recent = history_context + "\n" + new_context + f"\nHermes: {reply}"
        updated = await claude.update_memory(memory_content, recent, room_name)
        if updated and len(updated) > 100:
            save_memory(memory_file, updated)

async def main():
    setup_logging()
    log.info("=== Hermes NexTalk Bot starting ===")
    for d in [Path("/data/state"), Path("/data/logs"), Path("/data/memory"), Path("/data/backups")]:
        d.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    log.info(f"PID: {os.getpid()}")
    cfg = get_config()
    nc = NextcloudClient(cfg.nextcloud.url, cfg.nextcloud.user, cfg.nextcloud.pass_)
    claude = ClaudeClient(cfg.anthropic.api_key)
    urgent_mgr = UrgentModeManager()
    poll_state = load_poll_state()
    last_polled: dict[str, float] = {}
    log.info(f"Loaded {len(cfg.rooms)} rooms")
    for r in cfg.rooms:
        log.info(f"  {'ON' if r.enabled else 'OFF'} [L{r.level}] {r.name} ({r.role.value})")
    while True:
        try:
            HEARTBEAT_FILE.write_text(str(int(time.time())))
        except Exception:
            pass
        cfg = get_config()
        nc = NextcloudClient(cfg.nextcloud.url, cfg.nextcloud.user, cfg.nextcloud.pass_)
        claude = ClaudeClient(cfg.anthropic.api_key)
        now = time.time()
        for room in cfg.rooms:
            if not room.enabled:
                continue
            token = room.token
            base_interval = cfg.polling.level_intervals.get(str(room.level), 120)
            interval = urgent_mgr.get_effective_interval(token, base_interval, cfg.polling.urgent_poll_interval)
            if now - last_polled.get(token, 0) >= interval:
                try:
                    await process_room(token, room, poll_state, nc, claude, urgent_mgr, cfg)
                except Exception as e:
                    log.error(f"Error processing {room.name}: {e}", exc_info=True)
                last_polled[token] = now
        save_poll_state(poll_state)
        await asyncio.sleep(cfg.polling.tick)

if __name__ == "__main__":
    asyncio.run(main())
