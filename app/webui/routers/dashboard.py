from __future__ import annotations
import time
import json
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from webui.auth import is_authenticated
from shared.config import get_config

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
HEARTBEAT_FILE = Path("/data/state/heartbeat")
POLL_STATE_FILE = Path("/data/state/poll_state.json")
LOG_FILE = Path("/data/logs/poller.log")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    heartbeat_age = None
    poller_alive = False
    if HEARTBEAT_FILE.exists():
        try:
            last = int(HEARTBEAT_FILE.read_text())
            heartbeat_age = int(time.time()) - last
            poller_alive = heartbeat_age < 120
        except Exception:
            pass
    poll_state = {}
    if POLL_STATE_FILE.exists():
        try:
            poll_state = json.loads(POLL_STATE_FILE.read_text())
        except Exception:
            pass
    from poller.urgent import UrgentModeManager
    urgent_mgr = UrgentModeManager()
    rooms_status = []
    for r in cfg.rooms:
        rooms_status.append({"name": r.name, "token": r.token, "level": r.level, "enabled": r.enabled, "role": r.role.value, "last_id": poll_state.get(r.token, 0), "urgent": urgent_mgr.is_active(r.token)})
    return templates.TemplateResponse("dashboard.html", {"request": request, "poller_alive": poller_alive, "heartbeat_age": heartbeat_age, "rooms": rooms_status, "room_count": len([r for r in cfg.rooms if r.enabled])})

@router.get("/api/logs", response_class=PlainTextResponse)
async def get_logs(request: Request, lines: int = 100):
    if not is_authenticated(request):
        return PlainTextResponse("", status_code=401)
    if LOG_FILE.exists():
        try:
            all_lines = LOG_FILE.read_text(errors="replace").splitlines()
            return PlainTextResponse("\n".join(all_lines[-lines:]))
        except Exception:
            pass
    return PlainTextResponse("No logs yet.")
