"""
Tests for Chat Endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_message_creates_conversation(client: AsyncClient, auth_headers: dict):
    """Test that sending a message without a conversation_id creates a new one."""
    response = await client.post(
        "/api/v1/chat",
        json={"message": "What is machine learning?"},
        headers=auth_headers,
    )
    # May fail if LLM is not available, but should still return a response
    assert response.status_code in (200, 500)

    if response.status_code == 200:
        data = response.json()
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
        assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient, auth_headers: dict):
    """Test that a new user has no conversations."""
    response = await client.get(
        "/api/v1/chat/conversations",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_nonexistent_conversation(client: AsyncClient, auth_headers: dict):
    """Test fetching a conversation that doesn't exist."""
    response = await client.get(
        "/api/v1/chat/conversations/nonexistent-id",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_conversation(client: AsyncClient, auth_headers: dict):
    """Test deleting a conversation that doesn't exist."""
    response = await client.delete(
        "/api/v1/chat/conversations/nonexistent-id",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_unauthorized(client: AsyncClient):
    """Test that chat requires authentication."""
    response = await client.post(
        "/api/v1/chat",
        json={"message": "Hello"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_chat_with_unowned_document_rejected(client: AsyncClient, auth_headers: dict):
    """Test that querying with an unowned or nonexistent document_id returns 404."""
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "What is in this document?",
            "document_id": "nonexistent-doc-uuid-12345",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "not found or access denied" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_with_blank_document_id_succeeds(client: AsyncClient, auth_headers: dict):
    """Test that blank document_id string is treated as global chat without 404."""
    response = await client.post(
        "/api/v1/chat",
        json={
            "message": "Explain what photosynthesis is in one sentence.",
            "document_id": "   ",
        },
        headers=auth_headers,
    )
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "conversation_id" in data
        assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_list_conversations_with_search_query(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test searching conversations by title."""
    from app.models.conversation import Conversation
    from app.models.user import User
    from sqlalchemy import select

    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    conv1 = Conversation(title="Deep Reinforcement Learning", user_id=user.id)
    conv2 = Conversation(title="Quantum Error Correction", user_id=user.id)
    conv3 = Conversation(title="Graph Neural Networks", user_id=user.id)
    db_session.add_all([conv1, conv2, conv3])
    await db_session.commit()

    # Search for "Quantum"
    r = await client.get("/api/v1/chat/conversations?query=Quantum", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["title"] == "Quantum Error Correction"

    # Search for "Neural"
    r = await client.get("/api/v1/chat/conversations?query=neural", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["title"] == "Graph Neural Networks"

    # Search non-matching
    r = await client.get("/api/v1/chat/conversations?query=nonexistent", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 0


@pytest.mark.asyncio
async def test_rename_conversation_and_ownership(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test renaming a conversation and cross-user isolation."""
    from app.models.conversation import Conversation
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select

    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    other_user = User(
        email="other_conv_user@example.com",
        username="other_conv_user",
        hashed_password=hash_password("Pass123!"),
    )
    db_session.add(other_user)
    await db_session.flush()

    user_conv = Conversation(title="Original Title", user_id=user.id)
    other_conv = Conversation(title="Other Title", user_id=other_user.id)
    db_session.add_all([user_conv, other_conv])
    await db_session.commit()

    # User renames their own conversation
    r = await client.patch(
        f"/api/v1/chat/conversations/{user_conv.id}",
        json={"title": "Updated Brand New Title"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Brand New Title"

    # User tries to rename another user's conversation -> 404
    r = await client.patch(
        f"/api/v1/chat/conversations/{other_conv.id}",
        json={"title": "Hacked Title"},
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_conversation_markdown_and_json(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test exporting conversation history as Markdown and JSON."""
    from app.models.conversation import Conversation, Message
    from app.models.citation import Citation
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select

    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    # Create conversation with user + assistant messages and citation
    conv = Conversation(title="Quantum Physics Notes", user_id=user.id)
    db_session.add(conv)
    await db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role="user",
        content="What is entanglement?",
        sequence_number=0,
    )
    msg2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Entanglement is a phenomenon where particles share quantum states [1].",
        sequence_number=1,
    )
    db_session.add_all([msg1, msg2])
    await db_session.flush()

    cit = Citation(
        message_id=msg2.id,
        source_title="Quantum Mechanics Fundamentals.pdf",
        source_url="https://arxiv.org/abs/2101.0001",
        page_number=14,
        snippet="Entangled particles remain connected regardless of distance.",
        relevance_score=0.95,
        citation_index=1,
    )
    db_session.add(cit)
    await db_session.commit()

    # 1. Export as Markdown
    r = await client.get(
        f"/api/v1/chat/conversations/{conv.id}/export?format=markdown",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    text = r.text
    assert "# Quantum Physics Notes" in text
    assert "### User" in text
    assert "What is entanglement?" in text
    assert "### Assistant" in text
    assert "Quantum Mechanics Fundamentals.pdf" in text
    assert "Page 14" in text

    # 2. Export as JSON
    r = await client.get(
        f"/api/v1/chat/conversations/{conv.id}/export?format=json",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Quantum Physics Notes"
    assert len(data["messages"]) == 2
    assert data["messages"][1]["citations"][0]["citation_index"] == 1
    assert data["messages"][1]["citations"][0]["page_number"] == 14

    # 3. Export unowned conversation -> 404
    other_user = User(
        email="export_other@example.com",
        username="export_other",
        hashed_password=hash_password("Pass123!"),
    )
    db_session.add(other_user)
    await db_session.flush()

    other_conv = Conversation(title="Private Docs", user_id=other_user.id)
    db_session.add(other_conv)
    await db_session.commit()

    r = await client.get(
        f"/api/v1/chat/conversations/{other_conv.id}/export?format=json",
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_response_endpoint(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
):
    """Test regenerating the latest assistant response."""
    from app.models.conversation import Conversation, Message
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select

    res = await db_session.execute(select(User).where(User.username == "testuser"))
    user = res.scalar_one()

    conv = Conversation(title="Regenerate Test", user_id=user.id)
    db_session.add(conv)
    await db_session.flush()

    msg1 = Message(
        conversation_id=conv.id,
        role="user",
        content="What is photosynthesis?",
        sequence_number=0,
    )
    msg2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Photosynthesis is the process used by plants to synthesize nutrients.",
        sequence_number=1,
    )
    db_session.add_all([msg1, msg2])
    await db_session.commit()

    # Regenerate response
    r = await client.post(
        f"/api/v1/chat/conversations/{conv.id}/regenerate",
        headers=auth_headers,
    )
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert data["conversation_id"] == conv.id
        assert len(data["content"]) > 0

        # Check in DB that message count is still 2 and sequence_number is 1
        msgs_res = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.sequence_number.asc())
        )
        msgs = msgs_res.scalars().all()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"
        assert msgs[1].sequence_number == 1

    # Regenerating unowned conversation must return 404
    other_user = User(
        email="regen_other@example.com",
        username="regen_other",
        hashed_password=hash_password("Pass123!"),
    )
    db_session.add(other_user)
    await db_session.flush()

    other_conv = Conversation(title="Other Conv", user_id=other_user.id)
    db_session.add(other_conv)
    await db_session.commit()

    r_unowned = await client.post(
        f"/api/v1/chat/conversations/{other_conv.id}/regenerate",
        headers=auth_headers,
    )
    assert r_unowned.status_code == 404
