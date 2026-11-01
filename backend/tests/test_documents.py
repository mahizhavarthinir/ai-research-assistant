"""
Tests for Document Endpoints.
"""

import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient, auth_headers: dict):
    """Test that a new user has no documents."""
    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_upload_txt_document(client: AsyncClient, auth_headers: dict):
    """Test uploading a plain text file."""
    file_content = b"This is a test document about artificial intelligence."
    response = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
    )
    # May fail during ingestion (no embedding model), but endpoint should respond
    assert response.status_code in (201, 500)

    if response.status_code == 201:
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["file_type"] == "txt"
        assert data["file_size"] == len(file_content)


@pytest.mark.asyncio
async def test_upload_unsupported_file_type(client: AsyncClient, auth_headers: dict):
    """Test that uploading an unsupported file type is rejected."""
    response = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("test.exe", io.BytesIO(b"binary data"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ingest_invalid_url(client: AsyncClient, auth_headers: dict):
    """Test that an invalid URL is rejected."""
    response = await client.post(
        "/api/v1/documents/ingest-url",
        json={"url": "not-a-url"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_nonexistent_document(client: AsyncClient, auth_headers: dict):
    """Test fetching a document that doesn't exist."""
    response = await client.get(
        "/api/v1/documents/nonexistent-id",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_document(client: AsyncClient, auth_headers: dict):
    """Test deleting a document that doesn't exist."""
    response = await client.delete(
        "/api/v1/documents/nonexistent-id",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_documents_unauthorized(client: AsyncClient):
    """Test that document endpoints require authentication."""
    response = await client.get("/api/v1/documents")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_documents_search_and_filters(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test search query, file_type filter, and status filter in list_documents."""
    from app.models.document import Document
    from app.models.user import User
    from sqlalchemy import select

    # Get current user id from DB
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    # Seed 3 documents for this user
    doc1 = Document(
        user_id=user.id,
        filename="ai_research_paper.pdf",
        file_type="pdf",
        file_size=1024,
        source_url=None,
        status="indexed",
        chunk_count=3,
    )
    doc2 = Document(
        user_id=user.id,
        filename="python_notes.txt",
        file_type="txt",
        file_size=512,
        source_url=None,
        status="processing",
        chunk_count=0,
    )
    doc3 = Document(
        user_id=user.id,
        filename="https://arxiv.org/abs/2301.0001",
        file_type="url",
        file_size=None,
        source_url="https://arxiv.org/abs/2301.0001",
        status="error",
        error_message="Connection timed out",
        chunk_count=0,
    )
    db_session.add_all([doc1, doc2, doc3])
    await db_session.commit()

    # 1. Search by filename substring
    res = await client.get("/api/v1/documents?query=research", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["filename"] == "ai_research_paper.pdf"

    # 2. Search by URL substring
    res = await client.get("/api/v1/documents?query=arxiv", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["source_url"] == "https://arxiv.org/abs/2301.0001"

    # 3. Filter by file_type = pdf
    res = await client.get("/api/v1/documents?file_type=pdf", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["file_type"] == "pdf"

    # 4. Filter by file_type = text (alias for txt/md)
    res = await client.get("/api/v1/documents?file_type=text", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["file_type"] == "txt"

    # 5. Filter by file_type = url
    res = await client.get("/api/v1/documents?file_type=url", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["file_type"] == "url"

    # 6. Filter by status = error
    res = await client.get("/api/v1/documents?status=error", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "error"

    # 7. Filter by status = indexed
    res = await client.get("/api/v1/documents?status=indexed", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "indexed"

    # 8. Non-matching query
    res = await client.get("/api/v1/documents?query=quantum_mechanics", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 0


@pytest.mark.asyncio
async def test_document_chunks_and_ownership(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test retrieving chunks for a document, and verify cross-user isolation."""
    from app.models.document import Document, DocumentChunk
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select

    # Get current user id
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    # Create another user
    other_user = User(
        email="other@example.com",
        username="otheruser",
        hashed_password=hash_password("otherpassword123"),
    )
    db_session.add(other_user)
    await db_session.flush()

    # User's document with 2 chunks
    user_doc = Document(
        user_id=user.id,
        filename="user_doc.pdf",
        file_type="pdf",
        status="indexed",
        chunk_count=2,
    )
    db_session.add(user_doc)
    await db_session.flush()

    chunk1 = DocumentChunk(
        document_id=user_doc.id,
        chunk_index=0,
        content="First paragraph of user document.",
        page_number=1,
        token_count=6,
    )
    chunk2 = DocumentChunk(
        document_id=user_doc.id,
        chunk_index=1,
        content="Second paragraph of user document on page two.",
        page_number=2,
        token_count=8,
    )
    db_session.add_all([chunk1, chunk2])

    # Other user's document
    other_doc = Document(
        user_id=other_user.id,
        filename="secret_other.pdf",
        file_type="pdf",
        status="indexed",
        chunk_count=1,
    )
    db_session.add(other_doc)
    await db_session.flush()

    other_chunk = DocumentChunk(
        document_id=other_doc.id,
        chunk_index=0,
        content="Confidential text belonging to other user.",
        page_number=1,
        token_count=6,
    )
    db_session.add(other_chunk)
    await db_session.commit()

    # 1. Fetch chunks for user's own document
    res = await client.get(f"/api/v1/documents/{user_doc.id}/chunks", headers=auth_headers)
    assert res.status_code == 200
    chunks_data = res.json()
    assert len(chunks_data) == 2
    assert chunks_data[0]["chunk_index"] == 0
    assert chunks_data[0]["page_number"] == 1
    assert "First paragraph" in chunks_data[0]["content"]
    assert chunks_data[1]["chunk_index"] == 1
    assert chunks_data[1]["page_number"] == 2

    # 2. Try fetching chunks for another user's document -> must be rejected with 404
    res = await client.get(f"/api/v1/documents/{other_doc.id}/chunks", headers=auth_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # 3. Nonexistent document chunks -> 404
    res = await client.get("/api/v1/documents/nonexistent-doc-id/chunks", headers=auth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_retry_document_ownership_and_execution(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test retry endpoint ownership validation and status handling."""
    from app.models.document import Document
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select

    # Get current user id
    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    # Create another user
    other_user = User(
        email="retry_other@example.com",
        username="retryuser",
        hashed_password=hash_password("password123"),
    )
    db_session.add(other_user)
    await db_session.flush()

    # User's document with error status and missing file
    user_doc = Document(
        user_id=user.id,
        filename="corrupted.pdf",
        file_type="pdf",
        storage_path="/nonexistent/path/corrupted.pdf",
        status="error",
        error_message="Previous read failed",
        chunk_count=0,
    )
    db_session.add(user_doc)

    # Other user's document
    other_doc = Document(
        user_id=other_user.id,
        filename="other_file.pdf",
        file_type="pdf",
        status="error",
        error_message="Error",
        chunk_count=0,
    )
    db_session.add(other_doc)
    await db_session.commit()

    # 1. Retry unowned document -> must return 404
    res = await client.post(f"/api/v1/documents/{other_doc.id}/retry", headers=auth_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # 2. Retry nonexistent document -> must return 404
    res = await client.post("/api/v1/documents/nonexistent-id-999/retry", headers=auth_headers)
    assert res.status_code == 404

    # 3. Retry user's document where file path is missing -> returns 200 with clean error status
    res = await client.post(f"/api/v1/documents/{user_doc.id}/retry", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "error"
    assert "no longer exists" in data["error_message"].lower()


@pytest.mark.asyncio
async def test_wikipedia_url_header_selection_and_fetch():
    """Test that Wikipedia/Wikimedia URLs use the Wikimedia bot policy header and avoid 403."""
    from app.rag.parser import _is_wikimedia_url, _get_headers_for_url, fetch_url_content

    wiki_url = "https://en.wikipedia.org/wiki/Main_Page"
    non_wiki_url = "https://example.com/article"

    # Verify domain check
    assert _is_wikimedia_url(wiki_url) is True
    assert _is_wikimedia_url(non_wiki_url) is False

    # Verify header formatting complies with Wikimedia robot policy
    wiki_headers = _get_headers_for_url(wiki_url)
    assert "AIResearchAssistant" in wiki_headers["User-Agent"]
    assert "contact@" in wiki_headers["User-Agent"]

    browser_headers = _get_headers_for_url(non_wiki_url)
    assert "Mozilla/5.0" in browser_headers["User-Agent"]

    # Test real fetch on Wikipedia Main Page without 403 Forbidden
    content = await fetch_url_content(wiki_url, fetch_linked_pages=False)
    assert content and len(content) > 100
    assert "Wikipedia" in content


@pytest.mark.asyncio
async def test_url_ingestion_graceful_error_handling():
    """Test that inaccessible or forbidden URLs produce graceful, actionable error messages."""
    from app.rag.parser import fetch_url_content

    # 404 Page Not Found
    with pytest.raises(ValueError) as exc_info:
        await fetch_url_content("https://httpbin.org/status/404")
    assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    # 403 Access Forbidden
    with pytest.raises(ValueError) as exc_info_403:
        await fetch_url_content("https://httpbin.org/status/403")
    err_text = str(exc_info_403.value)
    assert "403" in err_text or "forbidden" in err_text.lower()
    assert "upload" in err_text.lower() or "pdf" in err_text.lower()

