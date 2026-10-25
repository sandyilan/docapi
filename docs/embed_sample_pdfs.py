from pathlib import Path

from ollama import embed
from pypdf import PdfReader
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Chunk, Document, Tenant


project_dir = Path(__file__).resolve().parents[1]
pdf_dir = project_dir / "docs" / "sample_pdfs"
embedding_model = "nomic-embed-text"


with SessionLocal() as db:
    tenant = db.scalar(select(Tenant).where(Tenant.name == "default"))
    if tenant is None:
        raise RuntimeError("The default tenant was not found.")

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError(f"No PDFs found in {pdf_dir}")

    for pdf_path in pdf_files:
        document = db.scalar(
            select(Document).where(
                Document.filename == pdf_path.name,
                Document.tenant_id == tenant.tenant_id,
            )
        )
        if document is None:
            print(f"Skipped {pdf_path.name}: upload it through the API first.")
            continue

        existing_chunk = db.scalar(
            select(Chunk.chunk_id)
            .where(Chunk.document_id == document.document_id)
            .limit(1)
        )
        if existing_chunk is not None:
            print(f"Skipped {pdf_path.name}: chunks already exist.")
            continue

        stored_path = Path(document.storage_path)
        if not stored_path.is_absolute():
            stored_path = project_dir / stored_path

        reader = PdfReader(str(stored_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            print(f"Skipped {pdf_path.name}: no extractable text.")
            continue

        result = embed(model=embedding_model, input=text)
        vector = result.embeddings[0]
        if len(vector) != 768:
            raise RuntimeError(
                f"Expected 768 numbers, received {len(vector)} for {pdf_path.name}."
            )

        db.add(
            Chunk(
                tenant_id=document.tenant_id,
                document_id=document.document_id,
                chunk_index=0,
                content=text,
                embedding=vector,
            )
        )
        db.commit()
        print(f"Embedded {pdf_path.name}: document {document.document_id}")


print("Finished processing sample PDFs.")