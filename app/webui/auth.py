from __future__ import annotations
import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from shared.config import get_config

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def is_authenticated(request: Request) -> bool:
    cfg = get_config()
    if not cfg.webui.auth_enabled:
        return True
    return request.cookies.get("htb_session") == "authenticated"
