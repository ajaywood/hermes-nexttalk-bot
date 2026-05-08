from __future__ import annotations
import time
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from shared.config import get_config, seed_from_env
from webui.auth import verify_password, is_authenticated
from webui.routers import dashboard, config as config_router, memory as memory_router

app = FastAPI(title="Hermes NexTalk Bot", docs_url=None, redoc_url=None)
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.include_router(dashboard.router)
app.include_router(config_router.router)
app.include_router(memory_router.router)
HEARTBEAT_FILE = Path("/data/state/heartbeat")

@app.on_event("startup")
async def startup():
    seed_from_env(get_config())
    scheduler = AsyncIOScheduler(timezone="Australia/Adelaide")
    scheduler.add_job(_daily_backup, CronTrigger(hour=2, minute=0))
    scheduler.start()

async def _daily_backup():
    from poller.memory import backup_all_rooms, cleanup_old_backups
    cfg = get_config()
    files = [r.memory_file for r in cfg.rooms if r.memory_file]
    backup_all_rooms(files)
    cleanup_old_backups(cfg.backup_retention_days)

@app.get("/health")
async def health():
    heartbeat_age = None
    poller_alive = False
    if HEARTBEAT_FILE.exists():
        try:
            last = int(HEARTBEAT_FILE.read_text())
            heartbeat_age = int(time.time()) - last
            poller_alive = heartbeat_age < 120
        except Exception:
            pass
    from poller.urgent import UrgentModeManager
    urgent_mgr = UrgentModeManager()
    cfg = get_config()
    urgent_active = any(urgent_mgr.is_active(r.token) for r in cfg.rooms if r.urgent_capable)
    return JSONResponse(
        content={"status": "ok" if poller_alive else "degraded", "poller_alive": poller_alive, "heartbeat_age_seconds": heartbeat_age, "urgent_mode_active": urgent_active},
        status_code=200 if poller_alive else 503
    )

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/")
    return templates.TemplateResponse(request, "login.html", {"error": None})

@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    password = form.get("password", "")
    cfg = get_config()
    if verify_password(str(password), cfg.webui.password_hash):
        response = RedirectResponse("/", status_code=302)
        response.set_cookie("htb_session", "authenticated", httponly=True, samesite="lax")
        return response
    return templates.TemplateResponse(request, "login.html", {"error": "Incorrect password"})

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("htb_session")
    return response
