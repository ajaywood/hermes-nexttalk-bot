from __future__ import annotations
import shutil
import logging
from datetime import datetime, date
from pathlib import Path

log = logging.getLogger(__name__)
MEMORY_DIR = Path("/data/memory")
BACKUP_DIR = Path("/data/backups")
VERSION_DIR = Path("/data/memory_versions")
MAX_VERSIONS = 5

def ensure_dirs() -> None:
    for d in [MEMORY_DIR, BACKUP_DIR, VERSION_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def load_memory(filename: str) -> str:
    ensure_dirs()
    path = MEMORY_DIR / filename
    if path.exists():
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception as e:
            log.error(f"Failed to load memory {filename}: {e}")
    return ""

def save_memory(filename: str, content: str) -> None:
    ensure_dirs()
    path = MEMORY_DIR / filename
    if path.exists():
        vdir = VERSION_DIR / filename
        vdir.mkdir(parents=True, exist_ok=True)
        versions = sorted(vdir.glob("*.md"))
        if len(versions) >= MAX_VERSIONS:
            versions[0].unlink(missing_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, vdir / f"{ts}.md")
    try:
        path.write_text(content, encoding="utf-8")
        log.info(f"Memory saved: {filename}")
    except Exception as e:
        log.error(f"Failed to save memory {filename}: {e}")

def backup_all_rooms(room_memory_files: list[str]) -> None:
    ensure_dirs()
    today = date.today().isoformat()
    backup_path = BACKUP_DIR / today
    backup_path.mkdir(parents=True, exist_ok=True)
    count = 0
    for filename in room_memory_files:
        src = MEMORY_DIR / filename
        if src.exists():
            shutil.copy2(src, backup_path / filename)
            count += 1
    log.info(f"Backed up {count} memory files to {backup_path}")

def cleanup_old_backups(retention_days: int = 30) -> None:
    ensure_dirs()
    cutoff = date.today().toordinal() - retention_days
    for d in BACKUP_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            backup_date = date.fromisoformat(d.name)
            if backup_date.day == 1:
                continue
            if backup_date.toordinal() < cutoff:
                shutil.rmtree(d)
                log.info(f"Removed old backup: {d.name}")
        except ValueError:
            continue

def list_versions(filename: str) -> list[str]:
    vdir = VERSION_DIR / filename
    if not vdir.exists():
        return []
    return sorted([v.stem for v in vdir.glob("*.md")], reverse=True)

def restore_version(filename: str, version_ts: str) -> bool:
    vdir = VERSION_DIR / filename
    src = vdir / f"{version_ts}.md"
    if not src.exists():
        return False
    shutil.copy2(src, MEMORY_DIR / filename)
    log.info(f"Restored {filename} from version {version_ts}")
    return True

def list_backups() -> dict[str, list[str]]:
    result = {}
    if not BACKUP_DIR.exists():
        return result
    for d in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if d.is_dir():
            result[d.name] = [f.name for f in sorted(d.glob("*.md"))]
    return result

def restore_backup(filename: str, backup_date: str) -> bool:
    src = BACKUP_DIR / backup_date / filename
    if not src.exists():
        return False
    shutil.copy2(src, MEMORY_DIR / filename)
    log.info(f"Restored {filename} from backup {backup_date}")
    return True
