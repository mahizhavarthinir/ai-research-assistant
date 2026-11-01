"""
Tests for Authentication Endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test user registration with valid data."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test that registering with an existing email fails."""
    payload = {
        "email": "dup@example.com",
        "username": "user1",
        "password": "testpassword123",
    }
    await client.post("/api/v1/auth/register", json=payload)

    payload["username"] = "user2"
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "email already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    """Test that registering with an existing username fails."""
    payload = {
        "email": "u1@example.com",
        "username": "sameuser",
        "password": "testpassword123",
    }
    await client.post("/api/v1/auth/register", json=payload)

    payload["email"] = "u2@example.com"
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "username" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test that a short password is rejected."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "short",
        },
    )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test login with valid credentials."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "mypassword123",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "mypassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong@example.com",
            "username": "wrongpw",
            "password": "correctpassword",
        },
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "incorrectpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with a non-existent email."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "doesntmatter",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, auth_headers: dict):
    """Test fetching the authenticated user's profile."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """Test that /me returns 401 without a token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_headers: dict):
    """Test logout endpoint."""
    response = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()
