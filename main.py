import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.api.v1.endpoints.pipeline_router import router as pipeline_router
from src.api.health import router as health_router
from src.pipeline.state_manager import data_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend-react"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await data_store.init_db()
    if not settings.GITHUB_TOKEN:
        logging.getLogger(__name__).warning(
            "GITHUB_TOKEN is not set. GitHub Models will be skipped; set GEMINI_API_KEY as fallback."
        )
    if not settings.GEMINI_API_KEY:
        logging.getLogger(__name__).warning(
            "GEMINI_API_KEY is not set. No Gemini fallback if GitHub Models fails or is rate-limited."
        )
    if not settings.GITHUB_TOKEN and not settings.GEMINI_API_KEY:
        logging.getLogger(__name__).error(
            "Neither GITHUB_TOKEN nor GEMINI_API_KEY is set. Translation and summarization will fail."
        )
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Video Processing & Analysis Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.OPENAPI_ENABLED else None,
    redoc_url="/redoc" if settings.OPENAPI_ENABLED else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pipeline_router, prefix=settings.API_V1_STR, tags=["Pipeline"])

if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
