from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from typing import Optional
import bcrypt
from .models import AppConfig, RoomConfig, RoomRole

CONFIG_PATH = Path("/data/config.json")
RELOAD_FLAG = Path("/data/state/.reload")

_config_cache: Optional[AppConfig] = None

def default_rooms() -> list[RoomConfig]:
    return [
        RoomConfig(token="9o27k98q", name="Mind & Growth", role=RoomRole.business, level=1, memory_file="9o27k98q_mind_growth.md", enabled=True, urgent_capable=True, model="claude-sonnet-4-5"),
        RoomConfig(token="7bs35y6b", name="Lilly's Safe Space", role=RoomRole.lilly, level=1, memory_file="7bs35y6b_lilly_safespace.md", enabled=True, model="claude-sonnet-4-5"),
        RoomConfig(token="rik47xkh", name="James's Cool Space", role=RoomRole.james, level=1, memory_file="rik47xkh_james_coolspace.md", enabled=True, model="claude-sonnet-4-5"),
        RoomConfig(token="inv6d8nm", name="Family Circle", role=RoomRole.family_mediator, level=2, memory_file="inv6d8nm_family_circle.md", enabled=True, model="claude-sonnet-4-5"),
        RoomConfig(token="aftx8sgr", name="Health & Nutrition", role=RoomRole.business, level=2, memory_file="aftx8sgr_health_nutrition.md", enabled=True),
        RoomConfig(token="nr5zgnaa", name="Family HQ", role=RoomRole.business, level=2, memory_file="nr5zgnaa_family_hq.md", enabled=True),
        RoomConfig(token="6vqssgpp", name="AJW Business", role=RoomRole.business, level=3, memory_file="6vqssgpp_ajw_business.md", enabled=True),
        RoomConfig(token="jnhyax8d", name="Projects", role=RoomRole.business, level=3, memory_file="jnhyax8d_projects.md", enabled=True),
        RoomConfig(token="fhdu9ejb", name="Fitness", role=RoomRole.business, level=3, memory_file="fhdu9ejb_fitness.md", enabled=True),
        RoomConfig(token="axhzvwp4", name="Home & Jobs", role=RoomRole.business, level=3, memory_file="axhzvwp4_home_jobs.md", enabled=True),
        RoomConfig(token="emqf655e", name="Bali 26", role=RoomRole.business, level=4, memory_file="emqf655e_bali_26.md", enabled=True),
    ]

def load_config() -> AppConfig:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            cfg = AppConfig.model_validate(data)
        except Exception:
            cfg = AppConfig(rooms=default_rooms())
    else:
        cfg = AppConfig(rooms=default_rooms())
    cfg = seed_from_env(cfg)
    return cfg

def save_config(cfg: AppConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = cfg.model_dump(by_alias=True)
    tmp = tempfile.NamedTemporaryFile(mode="w", dir=CONFIG_PATH.parent, delete=False, suffix=".tmp")
    try:
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.close()
        os.replace(tmp.name, CONFIG_PATH)
    except Exception:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise

def get_config() -> AppConfig:
    global _config_cache
    if RELOAD_FLAG.exists():
        try:
            RELOAD_FLAG.unlink()
        except Exception:
            pass
        _config_cache = None
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache

def invalidate_cache() -> None:
    global _config_cache
    _config_cache = None

def trigger_reload() -> None:
    RELOAD_FLAG.parent.mkdir(parents=True, exist_ok=True)
    RELOAD_FLAG.touch()

def seed_from_env(cfg: AppConfig) -> AppConfig:
    changed = False
    # NC_PASSWORD is the canonical env var; NC_PASS is an alias
    env_map = {
        "ANTHROPIC_API_KEY": ("anthropic", "api_key"),
        "NC_URL": ("nextcloud", "url"),
        "NC_USER": ("nextcloud", "user"),
        "NC_PASSWORD": ("nextcloud", "pass_"),
        "NC_PASS": ("nextcloud", "pass_"),
        "TELEGRAM_BOT_TOKEN": ("telegram", "bot_token"),
        "TELEGRAM_CHAT_ID": ("telegram", "chat_id"),
    }
    for env_var, (section, field) in env_map.items():
        val = os.environ.get(env_var, "").strip()
        if val:
            # Always overwrite from env so .env changes take effect on restart
            setattr(getattr(cfg, section), field, val)
            changed = True
    if not cfg.webui.password_hash:
        pw = os.environ.get("WEBUI_PASSWORD", "changeme")
        cfg.webui.password_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        changed = True
    if changed:
        try:
            save_config(cfg)
        except Exception:
            pass
    return cfg
