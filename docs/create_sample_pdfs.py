from pathlib import Path
from textwrap import wrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


output_dir = Path("docs/sample_pdfs")
output_dir.mkdir(parents=True, exist_ok=True)

documents = {
    "01_database_indexes.pdf": [
        "Database Indexes",
        "A database index helps find rows faster without scanning every row in a table.",
        "Indexes are useful for columns that are searched or sorted often.",
        "Indexes use extra storage and can make writes slightly slower.",
    ],
    "02_postgresql_vectors.pdf": [
        "PostgreSQL Vector Search",
        "A vector is a list of numbers that represents the meaning of text.",
        "Similar pieces of text tend to have vectors that are close together.",
        "PostgreSQL with pgvector can compare vectors and find similar text.",
    ],
    "03_rag_workflow.pdf": [
        "Retrieval Augmented Generation",
        "RAG searches documents before asking a language model to answer.",
        "The application retrieves relevant text chunks from a database.",
        "It gives those chunks to the model so the answer can use the documents.",
    ],
    "04_tenant_isolation.pdf": [
        "Tenant Isolation",
        "A tenant is one customer or organization using an application.",
        "Every document and chunk should belong to a tenant.",
        "Search must filter by tenant so one customer cannot see another customer's data.",
    ],
    "05_document_chunking.pdf": [
        "Document Chunking",
        "Long documents are split into smaller pieces called chunks.",
        "Chunks should be small enough to search but large enough to keep useful context.",
        "A small overlap between chunks can preserve context at the boundaries.",
    ],
}

for filename, paragraphs in documents.items():
    path = output_dir / filename
    pdf = canvas.Canvas(str(path), pagesize=letter)

    text = pdf.beginText(50, letter[1] - 50)
    text.setFont("Helvetica", 11)

    for paragraph in paragraphs:
        for line in wrap(paragraph, width=85):
            text.textLine(line)
        text.textLine("")

    pdf.drawText(text)
    pdf.save()
    print(f"Created: {path}")