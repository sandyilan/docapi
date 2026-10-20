import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.config import get_settings
from app.schemas import DocumentOut

from app.errors import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED = {".pdf": "application/pdf", ".txt": "text/plain"}
CHUNK = 1024 * 1024  # 1 MB


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
):
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise UnsupportedFileTypeError("Only .pdf and .txt files are allowed")

    data = bytearray()
    while chunk := await file.read(CHUNK):
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB")

    if not data:
        raise HTTPException(422, "File is empty")
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise HTTPException(422, "File is not a valid PDF")
    if ext == ".txt":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(422, "Text file must be UTF-8")

    doc_id = uuid.uuid4().hex
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / f"{doc_id}{ext}").write_bytes(data)

    return DocumentOut(
        id=doc_id,
        title=title,
        filename=file.filename or f"{doc_id}{ext}",
        content_type=ALLOWED[ext],
        size_bytes=len(data),
        created_at=datetime.now(timezone.utc),
    )