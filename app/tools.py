from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document


def build_tools(db: Session, tenant_id: int):
    def lookup_record(document_id: int) -> dict[str, object]:
        """Look up document metadata for this tenant.

        Args:
            document_id: The ID of the document to look up.
        """
        document = db.scalar(
            select(Document).where(
                Document.document_id == document_id,
                Document.tenant_id == tenant_id,
            )
        )

        if document is None:
            return {"found": False, "document_id": document_id}

        return {
            "found": True,
            "document_id": document.document_id,
            "title": document.title,
            "filename": document.filename,
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
            "created_at": document.created_at.isoformat(),
        }

    def document_status(document_id: int) -> dict[str, object]:
        """Check whether a document has embedded chunks for this tenant.

        Args:
            document_id: The ID of the document to check.
        """
        document_exists = db.scalar(
            select(Document.document_id).where(
                Document.document_id == document_id,
                Document.tenant_id == tenant_id,
            )
        )

        if document_exists is None:
            return {"found": False, "document_id": document_id}

        filters = (
            Chunk.document_id == document_id,
            Chunk.tenant_id == tenant_id,
        )
        chunk_count = db.scalar(
            select(func.count(Chunk.chunk_id)).where(*filters)
        ) or 0
        embedded_count = db.scalar(
            select(func.count(Chunk.chunk_id)).where(
                *filters,
                Chunk.embedding.is_not(None),
            )
        ) or 0

        if chunk_count == 0:
            status = "not_indexed"
        elif embedded_count == chunk_count:
            status = "indexed"
        else:
            status = "partially_indexed"

        return {
            "found": True,
            "document_id": document_id,
            "status": status,
            "chunk_count": chunk_count,
            "embedded_chunk_count": embedded_count,
        }

    return [lookup_record, document_status]