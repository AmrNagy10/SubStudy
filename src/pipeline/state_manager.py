import time
import json
import logging
import aiosqlite
from uuid import UUID
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class JobStateManager:
    """Persistent async store for tracking pipeline tasks using SQLite."""
    
    def __init__(self):
        self.db_path = "substudy_jobs.db"
        
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    result TEXT,
                    error_message TEXT,
                    updated_at REAL NOT NULL
                )
            ''')
            await db.commit()
            logger.info("SQLite Database initialized for JobStateManager.")

    async def initialize_job(self, job_id: UUID) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO jobs (job_id, status, progress, result, error_message, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(job_id), "processing", 0.0, None, None, time.time()))
            await db.commit()

    async def update_job(self, job_id: UUID, status: str, progress: float = 0.0, result: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None) -> None:
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
                "updated_at": row["updated_at"]
            }

# Global shared instance
data_store = JobStateManager()