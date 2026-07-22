from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import aiosqlite

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
 telegram_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin','blocked')),
 encrypted_github_token BLOB, github_login TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 telegram_id INTEGER PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
 state TEXT NOT NULL DEFAULT 'idle', data_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL,
 repository TEXT, branch TEXT, zip_name TEXT, total_files INTEGER DEFAULT 0,
 uploaded_files INTEGER DEFAULT 0, failed_files INTEGER DEFAULT 0,
 status TEXT NOT NULL, details TEXT, started_at TEXT NOT NULL, finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_operations_user ON operations(telegram_id, started_at DESC);
"""

def utcnow() -> str: return datetime.now(timezone.utc).isoformat()

class Database:
    def __init__(self, database_url: str):
        if not database_url.startswith("sqlite:///"):
            raise ValueError("This package ships with SQLite. Use sqlite:///path.db")
        self.path = Path(database_url.removeprefix("sqlite:///"))

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA); await db.commit()

    async def register_user(self, telegram_id: int, username: str | None, full_name: str, is_admin: bool=False) -> None:
        now=utcnow(); role="admin" if is_admin else "user"
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO users(telegram_id,username,full_name,role,created_at,updated_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username,
            full_name=excluded.full_name, updated_at=excluded.updated_at""",(telegram_id,username,full_name,role,now,now))
            await db.execute("INSERT OR IGNORE INTO sessions(telegram_id,updated_at) VALUES(?,?)",(telegram_id,now)); await db.commit()

    async def get_user(self, telegram_id: int) -> dict[str,Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row; cur=await db.execute("SELECT * FROM users WHERE telegram_id=?",(telegram_id,)); row=await cur.fetchone(); return dict(row) if row else None

    async def save_token(self, telegram_id:int, encrypted:bytes, login:str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET encrypted_github_token=?,github_login=?,updated_at=? WHERE telegram_id=?",(encrypted,login,utcnow(),telegram_id)); await db.commit()

    async def clear_token(self, telegram_id:int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET encrypted_github_token=NULL,github_login=NULL,updated_at=? WHERE telegram_id=?",(utcnow(),telegram_id)); await db.commit()

    async def save_session(self, telegram_id:int, state:str, data:dict[str,Any]) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO sessions(telegram_id,state,data_json,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET state=excluded.state,data_json=excluded.data_json,updated_at=excluded.updated_at""",(telegram_id,state,json.dumps(data,ensure_ascii=False),utcnow())); await db.commit()

    async def get_session(self, telegram_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT state, data_json FROM sessions WHERE telegram_id=?", (telegram_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return {"state": row["state"], "data": json.loads(row["data_json"] or "{}")}

    async def start_operation(self, telegram_id:int, repository:str, branch:str, zip_name:str, total:int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("INSERT INTO operations(telegram_id,repository,branch,zip_name,total_files,status,started_at) VALUES(?,?,?,?,?,'running',?)",(telegram_id,repository,branch,zip_name,total,utcnow())); await db.commit(); return int(cur.lastrowid)

    async def finish_operation(self, op_id:int, uploaded:int, failed:int, status:str, details:str='') -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE operations SET uploaded_files=?,failed_files=?,status=?,details=?,finished_at=? WHERE id=?",(uploaded,failed,status,details,utcnow(),op_id)); await db.commit()

    async def recent_operations(self, telegram_id:int, limit:int=10) -> list[dict[str,Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory=aiosqlite.Row; cur=await db.execute("SELECT * FROM operations WHERE telegram_id=? ORDER BY id DESC LIMIT ?",(telegram_id,limit)); return [dict(r) for r in await cur.fetchall()]

    async def set_role(self, telegram_id:int, role:str) -> None:
        if role not in {'user','admin','blocked'}: raise ValueError('Invalid role')
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET role=?,updated_at=? WHERE telegram_id=?",(role,utcnow(),telegram_id)); await db.commit()
