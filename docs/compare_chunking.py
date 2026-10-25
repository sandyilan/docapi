from pathlib import Path

import tiktoken
from pypdf import PdfReader


pdf_dir = Path("docs/sample_pdfs")
encoding = tiktoken.get_encoding("cl100k_base")

chunk_size = 120
overlap = 50
recursive_base_size = chunk_size - overlap


def token_count(text: str) -> int:
    return len(encoding.encode(text))


def fixed_chunks(text: str) -> list[str]:
    tokens = encoding.encode(text)
    step = chunk_size - overlap
    return [
        encoding.decode(tokens[start : start + chunk_size])
        for start in range(0, len(tokens), step)
    ]


def recursive_parts(
    text: str,
    limit: int,
    separators: tuple[str, ...] = ("\n\n", "\n", ". ", " "),
) -> list[str]:
    if token_count(text) <= limit:
        return [text]

    separator = next((item for item in separators if item in text), None)
    if separator is None:
        tokens = encoding.encode(text)
        return [
            encoding.decode(tokens[start : start + limit])
            for start in range(0, len(tokens), limit)
        ]

    remaining = separators[separators.index(separator) + 1 :]
    parts = text.split(separator)
    result = []
    current = ""

    for part in parts:
        if not part:
            continue

        candidate = part if not current else current + separator + part

        if token_count(candidate) <= limit:
            current = candidate
            continue

        if current:
            result.append(current)
            current = ""

        if token_count(part) > limit:
            result.extend(recursive_parts(part, limit, remaining))
        else:
            current = part

    if current:
        result.append(current)

    return result


def recursive_chunks(text: str) -> list[str]:
    parts = recursive_parts(text, recursive_base_size)
    result = []
    previous_tokens = []

    for part in parts:
        part_tokens = encoding.encode(part)
        prefix = previous_tokens[-overlap:]
        result.append(encoding.decode(prefix + part_tokens))
        previous_tokens.extend(part_tokens)

    return result


documents = []
for pdf_path in sorted(pdf_dir.glob("*.pdf")):
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if text:
        documents.append(f"Document: {pdf_path.name}\n{text}")

if not documents:
    raise RuntimeError(f"No extractable text found in {pdf_dir}")

# Combine the short samples for this comparison only.
# Real application chunks stay within their own document.
corpus = "\n\n".join(documents)

fixed = fixed_chunks(corpus)
recursive = recursive_chunks(corpus)

print("Total tokens:", token_count(corpus))
print(f"Fixed-size chunks: {len(fixed)}")
print("Fixed chunk sizes:", [token_count(chunk) for chunk in fixed])
print(f"Recursive chunks: {len(recursive)}")
print("Recursive chunk sizes:", [token_count(chunk) for chunk in recursive])