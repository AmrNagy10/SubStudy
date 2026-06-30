import os

from fastapi import APIRouter

from src.core.config import settings
from src.pipeline.job_gate import job_gate
from src.pipeline.model_registry import model_registry

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


@router.get("/ready")
async def ready():
    silero_hub = os.path.join(settings.SILERO_VAD_DIR, "hubconf.py")
    checks = {
        "database": True,
        "temp_dir": os.path.isdir(settings.TEMP_DIR) and os.access(settings.TEMP_DIR, os.W_OK),
        "silero_model": os.path.isfile(silero_hub),
        "github_token": bool(settings.GITHUB_TOKEN),
        "gemini_api_key": bool(settings.GEMINI_API_KEY),
        "vad_loaded": model_registry.vad_loaded,
        "stt_loaded": model_registry.stt_loaded,
        "active_jobs": job_gate.active_count,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
    }

    required_ok = checks["temp_dir"] and checks["silero_model"]
    status = "ok" if required_ok else "degraded"
    if not checks["github_token"] and not checks["gemini_api_key"]:
        status = "degraded"

    return {"status": status, "checks": checks}
