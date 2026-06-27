import os
from fastapi import HTTPException, Request, UploadFile, Security, File, Form
from fastapi.security import APIKeyHeader
from src.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Could not validate API key")
    return api_key
async def verify_headers_and_metadata(
    request: Request, 
    file: UploadFile = File(...), 
    source_lang: str = Form(...), 
    target_lang: str = Form(...)
):
    """
    Fail-Fast Guard Layer executing prior to reading stream payload[cite: 31].
    """
    # 1. Protect against DoS via Content-Length Header check
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=413, detail=f"File size exceeds the {settings.MAX_FILE_SIZE_BYTES/(1024*1024)}MB MVP limit.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header format.")

    # 2. Validate Language constraints
    if source_lang not in settings.SUPPORTED_SOURCE_LANGS:
        raise HTTPException(status_code=400, detail=f"Invalid source language. Choose from {settings.SUPPORTED_SOURCE_LANGS}")
    if target_lang not in settings.SUPPORTED_TARGET_LANGS:
        raise HTTPException(status_code=400, detail=f"Invalid target language. Choose from {settings.SUPPORTED_TARGET_LANGS}")

    # 3. Validate Basic Extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing valid filename payload.")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_CONTAINERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported container format. Only {list(settings.ALLOWED_CONTAINERS)} are allowed."
        )

    return {
        "source_lang": source_lang,
        "target_lang": target_lang,
        "file_ext": file_ext
    }