import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.models import Chunk, Document, Tenant
from app.config import SettingsDep
from app.database import get_db
from app.errors import (
    FileTooLargeError,
    InvalidFileError,
    UnsupportedFileTypeError,
)
from app.ingestion import ingest_document
from app.models import Document, Tenant
from app.schemas import DocumentOut, DocumentUploadOut
from app.schemas import ChunkOut, DocumentOut, DocumentUploadOut

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED = {".pdf": "application/pdf", ".txt": "text/plain"}
CHUNK = 1024 * 1024  # 1 MB


@router.post("", response_model=DocumentUploadOut, status_code=201)
async def upload_document(
    settings: SettingsDep,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),  # noqa: B008
    title: str | None = Form(default=None),
):
    max_bytes = settings.max_upload_mb * 1024 * 1024

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise UnsupportedFileTypeError("Only .pdf and .txt files are allowed")

    data = bytearray()
    while chunk := await file.read(CHUNK):
        data.extend(chunk)
        if len(data) > max_bytes:
            raise FileTooLargeError(f"File exceeds {settings.max_upload_mb} MB")

    if not data:
        raise InvalidFileError("File is empty")
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise InvalidFileError("File is not a valid PDF")
    if ext == ".txt":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise InvalidFileError("Text file must be UTF-8") from None

    content_hash = hashlib.sha256(data).hexdigest()

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_path = upload_dir / f"{content_hash}{ext}"
    storage_path.write_bytes(data)

    tenant = db.scalar(select(Tenant).where(Tenant.name == "default"))
    if tenant is None:
        tenant = Tenant(name="default")
        db.add(tenant)
        db.flush()

    db.execute(
        pg_insert(Document)
        .values(
            tenant_id=tenant.tenant_id,
            title=title or file.filename or storage_path.name,
            filename=file.filename or storage_path.name,
            content_type=ALLOWED[ext],
            size_bytes=len(data),
            storage_path=str(storage_path),
            content_hash=content_hash,
        )
        .on_conflict_do_nothing(constraint="uq_documents_tenant_content_hash")
    )
    db.commit()

    document = db.scalar(
        select(Document).where(
            Document.tenant_id == tenant.tenant_id,
            Document.content_hash == content_hash,
        )
    )

    chunks_created = ingest_document(db, document)
    db.commit()

    return DocumentUploadOut(
        id=str(document.document_id),
        title=document.title,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
        chunks_created=chunks_created,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    tenant_id: int = Query(gt=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    documents = db.scalars(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [
        DocumentOut(
            id=str(document.document_id),
            title=document.title,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            created_at=document.created_at,
        )
        for document in documents
    ]

@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def list_document_chunks(
    document_id: int,
    tenant_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    document_exists = db.scalar(
        select(Document.document_id).where(
            Document.document_id == document_id,
            Document.tenant_id == tenant_id,
        )
    )

    if document_exists is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.scalars(
        select(Chunk)
        .where(
            Chunk.document_id == document_id,
            Chunk.tenant_id == tenant_id,
        )
        .order_by(Chunk.chunk_index)
    ).all()

    return [
        ChunkOut(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            has_embedding=chunk.embedding is not None,
        )
        for chunk in chunks
    ]