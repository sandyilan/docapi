from pathlib import Path

from ollama import embed
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chunking import chunk_text
from app.models import Chunk, Document


def ingest_document(db: Session, document: Document) -> int:
    existing_chunk = db.scalar(
        select(Chunk.chunk_id)
        .where(
            Chunk.document_id == document.document_id,
            Chunk.tenant_id == document.tenant_id,
        )
        .limit(1)
    )
    if existing_chunk is not None:
        return 0

    file_path = Path(document.storage_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if document.content_type == "application/pdf":
        reader = PdfReader(str(file_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    elif document.content_type == "text/plain":
        text = file_path.read_text(encoding="utf-8").strip()
    else:
        return 0

    text_chunks = chunk_text(text)
    new_chunks = []

    for index, content in enumerate(text_chunks):
        vector = embed(
            model="nomic-embed-text",
            input=content,
        ).embeddings[0]

        if len(vector) != 768:
            raise RuntimeError(
                f"Expected 768 embedding values, received {len(vector)}."
            )

        new_chunks.append(
            Chunk(
                tenant_id=document.tenant_id,
                document_id=document.document_id,
                chunk_index=index,
                content=content,
                embedding=vector,
            )
        )

    db.add_all(new_chunks)
    return len(new_chunks)