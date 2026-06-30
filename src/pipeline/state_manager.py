import time
import json
import logging
import aiosqlite
from uuid import UUID
from typing import Dict, Any, Optional

from src.core.config import settings

logger = logging.getLogger(__name__)

class JobStateManager:
    """Persistent async store for tracking pipeline tasks using SQLite."""
    
    def __init__(self):
        self.db_path = settings.DB_PATH
        
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    result TEXT,
                    error_message TEXT,
                    source_lang TEXT,
                    target_lang TEXT,
                    file_name TEXT,
                    updated_at REAL NOT NULL
                )
            ''')
            await db.commit()
            await self._migrate_schema(db)
            logger.info("SQLite Database initialized for JobStateManager.")

    async def _migrate_schema(self, db) -> None:
        cursor = await db.execute("PRAGMA table_info(jobs)")
        columns = {row[1] for row in await cursor.fetchall()}
        migrations = {
            "source_lang": "ALTER TABLE jobs ADD COLUMN source_lang TEXT",
            "target_lang": "ALTER TABLE jobs ADD COLUMN target_lang TEXT",
            "file_name": "ALTER TABLE jobs ADD COLUMN file_name TEXT",
        }
        for column, sql in migrations.items():
            if column not in columns:
                await db.execute(sql)
        await db.commit()

    async def initialize_job(
        self,
        job_id: UUID,
        source_lang: str | None = None,
        target_lang: str | None = None,
        file_name: str | None = None,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO jobs (
                    job_id, status, progress, result, error_message,
                    source_lang, target_lang, file_name, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(job_id), "processing", 0.0, None, None,
                source_lang, target_lang, file_name, time.time(),
            ))
            await db.commit()

    async def update_job(self, job_id: UUID, status: str, progress: float = 0.0, result: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None) -> None:
        current = await self.get_job(job_id)
        if current and current.get("status") == "canceled" and status != "canceled":
            return

        async with aiosqlite.connect(self.db_path) as db:
            updates = ["status = ?", "progress = ?", "updated_at = ?"]
            params = [status, progress, time.time()]
            
            if result is not None:
                updates.append("result = ?")
                params.append(json.dumps(result))
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
                
            params.append(str(job_id))
            
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
            await db.execute(query, tuple(params))
            await db.commit()

    async def get_job(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM jobs WHERE job_id = ?', (str(job_id),))
            row = await cursor.fetchone()
            
            if not row:
                return None
                
            return {
                "job_id": UUID(row["job_id"]),
                "status": row["status"],
                "progress": row["progress"],
                "result": json.loads(row["result"]) if row["result"] else None,
                "error_message": row["error_message"],
                "source_lang": row["source_lang"],
                "target_lang": row["target_lang"],
                "file_name": row["file_name"],
                "updated_at": row["updated_at"],
            }

    async def delete_job(self, job_id: UUID) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'DELETE FROM jobs WHERE job_id = ?', (str(job_id),)
            )
            await db.commit()
            return cursor.rowcount > 0

# Global shared instance
data_store = JobStateManager()