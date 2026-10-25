import tiktoken


encoding = tiktoken.get_encoding("cl100k_base")


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    tokens = encoding.encode(text)
    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(tokens), step):
        chunk = encoding.decode(tokens[start : start + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)

        if start + chunk_size >= len(tokens):
            break

    return chunks