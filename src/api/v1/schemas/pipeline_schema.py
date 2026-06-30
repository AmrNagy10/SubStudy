from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any

class PipelineInitResponse(BaseModel):
    job_id: UUID = Field(..., description="Unique token for checking background process status")
    status: str = Field("processing")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = Field("Processing initiated in background.")

class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str  # processing, completed, failed, canceled
    progress: float
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    file_name: Optional[str] = None