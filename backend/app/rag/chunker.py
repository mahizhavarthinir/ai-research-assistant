"""
AI Research Assistant — Text Chunker

Splits documents into overlapping chunks for embedding.
"""

from app.core.config import settings


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Split text into overlapping chunks without skipping any text.

    Returns a list of dicts: [{"content": str, "index": int, "char_start": int, "char_end": int}]
    """
    size = chunk_size or settings.CHUNK_SIZE
    overlap = chunk_overlap or settings.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    # Safeguard: overlap cannot equal or exceed size
    if overlap >= size:
        overlap = max(1, size // 4)

    text = text.strip()
    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = min(start + size, len(text))

        # Try to break at a sentence or paragraph boundary if not at the very end
        if end < len(text):
            for boundary_char in ["\n\n", "\n", ". ", "? ", "! ", "; ", " "]:
                boundary = text.rfind(boundary_char, start + size // 2, end)
                if boundary != -1:
                    end = boundary + len(boundary_char)
                    break

        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append({
                "content": chunk_content,
                "index": index,
                "char_start": start,
                "char_end": end,
            })
            index += 1

        # Advance start so that exactly `overlap` characters are shared with the next chunk
        # and no text between end and the next start is ever skipped.
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
        if start >= len(text):
            break

    return chunks
