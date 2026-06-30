import os
import uuid
import logging
import asyncio
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, Depends, BackgroundTasks

from src.api.v1.schemas.pipeline_schema import PipelineInitResponse, JobStatusResponse
from src.api.v1.dependencies import verify_headers_and_metadata, verify_api_key
from src.core.config import settings
from src.pipeline.orchestrator import run_pipeline_job
from src.pipeline.state_manager import data_store
from src.pipeline.job_gate import job_gate

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
    """Secure chunked ingestion and async hand-off."""
    job_id = uuid.uuid4()

    if not await job_gate.try_acquire(job_id):
        raise HTTPException(
            status_code=503,
            detail="Another job is already running. Wait for it to finish or cancel it first.",
        )

    file_ext = validated_data["file_ext"]
    temp_file_path = os.path.join(settings.TEMP_DIR, f"{job_id}{file_ext}")

    try:
        async with aiofiles.open(temp_file_path, "wb") as f:
            total_bytes_read = 0
            while True:
                chunk = await file.read(1 * 1024 * 1024)
                if not chunk:
                    break

                total_bytes_read += len(chunk)
                if total_bytes_read > settings.MAX_FILE_SIZE_BYTES:
                    await asyncio.to_thread(os.remove, temp_file_path)
                    await job_gate.release(job_id)
                    raise HTTPException(
                        status_code=413,
                        detail="Stream exceeded 500MB threshold during active download.",
                    )

                await f.write(chunk)

        logger.info(f"Payload securely written to storage: {temp_file_path}")

    except HTTPException:
        raise
    except Exception as e:
        if await asyncio.to_thread(os.path.exists, temp_file_path):
            await asyncio.to_thread(os.remove, temp_file_path)
        await job_gate.release(job_id)
        logger.error(f"Write failure for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server disk I/O breakdown.")

    await data_store.initialize_job(
        job_id,
        source_lang=validated_data["source_lang"],
        target_lang=validated_data["target_lang"],
        file_name=file.filename,
    )

    background_tasks.add_task(
        run_pipeline_job,
        job_id,
        temp_file_path,
        validated_data["source_lang"],
        validated_data["target_lang"],
    )

    return PipelineInitResponse(job_id=job_id)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: uuid.UUID):
    job = await data_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Target task pipeline '{job_id}' does not exist.")

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        error_message=job["error_message"],
        result=job["result"],
        source_lang=job.get("source_lang"),
        target_lang=job.get("target_lang"),
        file_name=job.get("file_name"),
    )


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: uuid.UUID):
    job = await data_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Target task pipeline '{job_id}' does not exist.")

    if job["status"] == "canceled":
        return {"detail": "canceled"}

    if job["status"] != "processing":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a job with status '{job['status']}'.",
        )

    await data_store.update_job(
        job_id, status="canceled", progress=job["progress"], error_message="Canceled by user"
    )
    await job_gate.release(job_id)
    logger.info("Job %s canceled by user; gate released.", job_id)
    return {"detail": "canceled"}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: uuid.UUID):
    job = await data_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Target task pipeline '{job_id}' does not exist.")

    if job["status"] == "processing":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a running job. Cancel it first, then delete.",
        )

    deleted = await data_store.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Target task pipeline '{job_id}' does not exist.")

    return {"detail": "deleted"}
