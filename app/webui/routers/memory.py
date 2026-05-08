from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from webui.auth import is_authenticated
from shared.config import get_config
from poller.memory import load_memory, save_memory, list_versions, restore_version, backup_all_rooms, list_backups

router = APIRouter(prefix="/memory")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

@router.get("", response_class=HTMLResponse)
async def memory_list(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    MEMORY_DIR = Path("/data/memory")
    rooms_info = []
    for r in cfg.rooms:
        if r.memory_file:
            p = MEMORY_DIR / r.memory_file
            rooms_info.append({"token": r.token, "name": r.name, "file": r.memory_file, "exists": p.exists(), "size": p.stat().st_size if p.exists() else 0, "modified": p.stat().st_mtime if p.exists() else None})
    backups = list_backups()
    return templates.TemplateResponse("memory.html", {"request": request, "rooms": rooms_info, "backups": backups})

@router.get("/{token}", response_class=HTMLResponse)
async def memory_edit(request: Request, token: str):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    room = next((r for r in cfg.rooms if r.token == token), None)
    if not room:
        return RedirectResponse("/memory")
    content = load_memory(room.memory_file) if room.memory_file else ""
    versions = list_versions(room.memory_file) if room.memory_file else []
    return templates.TemplateResponse("memory_edit.html", {"request": request, "room": room, "content": content, "versions": versions})

@router.post("/{token}")
async def memory_save(request: Request, token: str, content: str = Form("")):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    room = next((r for r in cfg.rooms if r.token == token), None)
    if room and room.memory_file:
        save_memory(room.memory_file, content)
    return RedirectResponse(f"/memory/{token}?saved=1", status_code=302)

@router.post("/{token}/backup")
async def memory_backup_now(request: Request, token: str):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    room = next((r for r in cfg.rooms if r.token == token), None)
    if room and room.memory_file:
        backup_all_rooms([room.memory_file])
    return RedirectResponse(f"/memory/{token}?backed_up=1", status_code=302)

@router.post("/{token}/restore/{version}")
async def memory_restore_version(request: Request, token: str, version: str):
    if not is_authenticated(request):
        return RedirectResponse("/login")
    cfg = get_config()
    room = next((r for r in cfg.rooms if r.token == token), None)
    if room and room.memory_file:
        restore_version(room.memory_file, version)
    return RedirectResponse(f"/memory/{token}?restored=1", status_code=302)
