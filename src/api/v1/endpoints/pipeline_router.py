import os
import uuid
import logging
import asyncio
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, Depends, BackgroundTasks

# Corrected clean import references based on exact visual map
from src.api.v1.schemas.pipeline_schema import PipelineInitResponse, JobStatusResponse
from src.api.v1.dependencies import verify_headers_and_metadata, verify_api_key
from src.core.config import settings
from src.pipeline.orchestrator import run_pipeline_job
from src.pipeline.state_manager import data_store

router = APIRouter(dependencies=[Depends(verify_api_key)])
logger = logging.getLogger(__name__)


@router.post("/process", response_model=PipelineInitResponse, status_code=202)
async def process_video(
        request: Request,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        source_lang: str = Form(...),
        target_lang: str = Form(...),
        validated_data: dict = Depends(verify_headers_and_metadata)
):
    """
    Secure Chunked Ingestion & Async Hand-off.
    """
    file_ext = validated_data["file_ext"]
    job_id = uuid.uuid4()
    temp_file_path = os.path.join(settings.TEMP_DIR, f"{job_id}{file_ext}")

    try:
        # Safe Chunked I/O Stream
        async with aiofiles.open(temp_file_path, "wb") as f:
            total_bytes_read = 0
            while True:
                chunk = await file.read(1 * 1024 * 1024)  # 1MB chunks
                if not chunk:
                    break

                total_bytes_read += len(chunk)
                # Deep defensive size verification
                if total_bytes_read > settings.MAX_FILE_SIZE_BYTES:
                    await asyncio.to_thread(os.remove, temp_file_path)
                    raise HTTPException(status_code=413,
                                        detail="Stream exceeded 500MB threshold during active download.")

                await f.write(chunk)

        logger.info(f"Payload securely written to storage: {temp_file_path}")

    except HTTPException:
        raise
    except Exception as e:
        if await asyncio.to_thread(os.path.exists, temp_file_path):
            await asyncio.to_thread(os.remove, temp_file_path)
        logger.error(f"Write failure for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server disk I/O breakdown.")

    # Task Handoff to background orchestrator
    background_tasks.add_task(
        run_pipeline_job,
        job_id,
        temp_file_path,
        validated_data["source_lang"],
        validated_data["target_lang"]
    )

    return PipelineInitResponse(job_id=job_id)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: uuid.UUID):
    """
    Polling target for tracking background workers and extracting final structured outputs.
    """
    job = await data_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Target task pipeline '{job_id}' does not exist.")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        error_message=job["error_message"],
        result=job["result"]
    )


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: uuid.UUID):
    """
    Cancel a running job. Marks the job state as 'canceled' so background workers can detect it.
    """
    job = await data_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Target task pipeline '{job_id}' does not exist.")

    await data_store.update_job(job_id, status="canceled", progress=100.0, error_message="Canceled by user")
    return {"detail": "canceled"}