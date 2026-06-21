#!/usr/bin/env python3
"""Create a safe SQLite backup of BEAN memory."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def load_env(path: str = "/etc/bean/bean.env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env()
    db_path = Path(os.environ.get("BEAN_DB_PATH", "/home/bean/bean_data/bean_memory.db"))
    backup_dir = Path(os.environ.get("BEAN_BACKUP_DIR", str(db_path.parent / "backups")))
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        print(f"BEAN DB not found: {db_path}")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = backup_dir / f"bean_memory_{stamp}.db"

    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(out_path))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    print(f"BEAN memory backup written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
