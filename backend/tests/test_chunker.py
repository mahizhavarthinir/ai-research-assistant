"""
Tests for the RAG Chunker utility.
"""

import pytest
from app.rag.chunker import chunk_text


def test_chunk_text_basic():
    """Test basic text chunking."""
    text = "Hello world. " * 100  # ~1300 chars
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert "content" in chunk
        assert "index" in chunk
        assert "char_start" in chunk
        assert "char_end" in chunk
        assert len(chunk["content"]) > 0


def test_chunk_text_empty():
    """Test chunking with empty text."""
    assert chunk_text("") == []
    assert chunk_text("   ") == []
    assert chunk_text(None) == []


def test_chunk_text_short():
    """Test chunking with text shorter than chunk_size."""
    text = "Short text."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0]["content"] == "Short text."
    assert chunks[0]["index"] == 0


def test_chunk_text_overlap():
    """Test that chunks overlap correctly."""
    text = "A " * 500  # 1000 chars
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)
    assert len(chunks) > 1

    # Each chunk's start should be less than the previous chunk's end
    for i in range(1, len(chunks)):
        assert chunks[i]["char_start"] < chunks[i - 1]["char_end"]


def test_chunk_indices_sequential():
    """Test that chunk indices are sequential."""
    text = "Word " * 200
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    for i, chunk in enumerate(chunks):
        assert chunk["index"] == i


def test_chunk_text_preserves_content():
    """Test that no content is lost during chunking."""
    text = "The quick brown fox jumps over the lazy dog. " * 50
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)

    # All text should be covered by at least one chunk
    covered = set()
    for chunk in chunks:
        for i in range(chunk["char_start"], chunk["char_end"]):
            covered.add(i)

    # Check that the full text range is covered
    for i in range(len(text.strip())):
        assert i in covered, f"Position {i} not covered by any chunk"
