import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.core.config import settings
from src.api.v1.endpoints.pipeline_router import router as pipeline_router
from src.pipeline.state_manager import data_store

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema before serving requests
    await data_store.init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Video Processing & Analysis Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(pipeline_router, prefix=settings.API_V1_STR, tags=["Pipeline"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
