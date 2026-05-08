from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from webui.auth import is_authenticated, hash_password
from shared.config import get_config, save_config, invalidate_cache, trigger_reload

router = APIRouter(prefix="/config")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

@router.get("", response_class=HTMLResponse)
async def config_get(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    return templates.TemplateResponse("config.html", {"request": request, "cfg": cfg})

@router.post("/credentials")
async def save_credentials(request: Request, nc_url: str = Form(""), nc_user: str = Form(""), nc_pass: str = Form(""), api_key: str = Form(""), default_model: str = Form(""), tg_token: str = Form(""), tg_chat_id: str = Form(""), new_password: str = Form("")):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    if nc_url: cfg.nextcloud.url = nc_url
    if nc_user: cfg.nextcloud.user = nc_user
    if nc_pass: cfg.nextcloud.pass_ = nc_pass
    if api_key: cfg.anthropic.api_key = api_key
    if default_model: cfg.anthropic.default_model = default_model
    if tg_token: cfg.telegram.bot_token = tg_token
    if tg_chat_id: cfg.telegram.chat_id = tg_chat_id
    if new_password: cfg.webui.password_hash = hash_password(new_password)
    save_config(cfg)
    invalidate_cache()
    trigger_reload()
    return RedirectResponse("/config?saved=1", status_code=302)

@router.post("/polling")
async def save_polling(request: Request, tick: int = Form(15), urgent_poll_interval: int = Form(15), urgent_calm_timeout: int = Form(600), urgent_trigger_words: str = Form(""), urgent_calm_words: str = Form(""), history_limit: int = Form(20), safety_keywords: str = Form(""), backup_retention_days: int = Form(30)):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    cfg.polling.tick = tick
    cfg.polling.urgent_poll_interval = urgent_poll_interval
    cfg.polling.urgent_calm_timeout = urgent_calm_timeout
    if urgent_trigger_words:
        cfg.polling.urgent_trigger_words = [w.strip() for w in urgent_trigger_words.split(",") if w.strip()]
    if urgent_calm_words:
        cfg.polling.urgent_calm_words = [w.strip() for w in urgent_calm_words.split(",") if w.strip()]
    cfg.polling.history_limit = history_limit
    if safety_keywords:
        cfg.safety_keywords = [w.strip() for w in safety_keywords.split("\n") if w.strip()]
    cfg.backup_retention_days = backup_retention_days
    save_config(cfg)
    invalidate_cache()
    trigger_reload()
    return RedirectResponse("/config?saved=1", status_code=302)

@router.post("/room/{token}")
async def save_room(request: Request, token: str, name: str = Form(""), role: str = Form("business"), level: int = Form(2), memory_file: str = Form(""), enabled: Optional[str] = Form(None), urgent_capable: Optional[str] = Form(None), model: str = Form(""), system_prompt_override: str = Form("")):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    for room in cfg.rooms:
        if room.token == token:
            if name: room.name = name
            room.role = role
            room.level = level
            if memory_file: room.memory_file = memory_file
            room.enabled = enabled is not None
            room.urgent_capable = urgent_capable is not None
            room.model = model if model and model != "default" else None
            room.system_prompt_override = system_prompt_override or None
            break
    save_config(cfg)
    invalidate_cache()
    trigger_reload()
    return RedirectResponse("/config?saved=1", status_code=302)
