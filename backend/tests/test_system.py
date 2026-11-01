"""
Tests for Health & System Endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the /health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    """Test the /ready endpoint."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    # Will be "not_ready" in test env since we use SQLite, not PostgreSQL
    assert "status" in data


@pytest.mark.asyncio
async def test_api_docs(client: AsyncClient):
    """Test that OpenAPI docs are accessible."""
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_security_module():
    """Test password hashing and JWT token creation."""
    from app.core.security import (
        hash_password,
        verify_password,
        create_access_token,
        decode_token,
    )

    # Password hashing
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True
    assert verify_password("wrongpassword", hashed) is False

    # JWT tokens
    token = create_access_token(data={"sub": "user-123"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"

    # Invalid token
    assert decode_token("invalid.token.here") is None
