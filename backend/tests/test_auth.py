"""Tests for authentication, organization creation, and JWT refresh token rotation."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_creates_personal_org_and_tokens(client: AsyncClient):
    """Registering creates user, personal org, owner membership, and returns tokens."""
    payload = {
        "email": "lead@archstudio.com",
        "password": "SecurePassword123!",
        "full_name": "Lead Architect",
        "org_name": "ArchStudio",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["full_name"] == payload["full_name"]
    assert data["org"]["name"] == payload["org_name"]
    assert "id" in data["org"]


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    """Attempting to register with an existing email returns 409 and standard error shape."""
    payload = {
        "email": "duplicate@archstudio.com",
        "password": "SecurePassword123!",
        "full_name": "Duplicate User",
        "org_name": "ArchStudio",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    error = res2.json()
    assert error["code"] == "EMAIL_ALREADY_EXISTS"
    assert "message" in error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Logging in with valid credentials returns access and refresh tokens."""
    payload = {
        "email": "login_test@archstudio.com",
        "password": "MyStrongPassword123!",
        "full_name": "Login Tester",
        "org_name": "Tester Org",
    }
    await client.post("/api/v1/auth/register", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_bad_password_fails(client: AsyncClient):
    """Logging in with incorrect password returns 401 with standard error shape."""
    payload = {
        "email": "bad_pw@archstudio.com",
        "password": "CorrectPassword123!",
        "full_name": "Bad PW Tester",
    }
    await client.post("/api/v1/auth/register", json=payload)

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "WrongPassword123!"},
    )
    assert login_resp.status_code == 401
    error = login_resp.json()
    assert error["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    """Refresh tokens are single-use and rotate. Old refresh token cannot be reused."""
    payload = {
        "email": "rotation@archstudio.com",
        "password": "Password123!Rotate",
        "full_name": "Rotate Tester",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201
    old_refresh_token = reg_resp.json()["refresh_token"]

    # First refresh: should succeed and provide a new refresh token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    new_access_token = data["access_token"]
    new_refresh_token = data["refresh_token"]
    assert new_access_token is not None
    assert new_refresh_token != old_refresh_token

    # Replay attack: using the old refresh token MUST fail with 401
    replay_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert replay_resp.status_code == 401
    error = replay_resp.json()
    assert error["code"] in ["INVALID_REFRESH_TOKEN", "TOKEN_REVOKED"]


@pytest.mark.asyncio
async def test_expired_or_invalid_jwt(client: AsyncClient):
    """Protected endpoints reject invalid or malformed tokens with 401."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.malformed.token"},
    )
    assert resp.status_code == 401
    error = resp.json()
    assert error["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: AsyncClient):
    """Logging out revokes the refresh token."""
    payload = {
        "email": "logout_test@archstudio.com",
        "password": "Password123!Logout",
        "full_name": "Logout Tester",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=payload)
    refresh_token = reg_resp.json()["refresh_token"]
    access_token = reg_resp.json()["access_token"]

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200

    # Attempting to refresh with the logged-out token must fail
    try_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert try_refresh.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, auth_org_a: dict):
    """GET /api/v1/auth/me returns the authenticated user profile and active organization."""
    resp = await client.get("/api/v1/auth/me", headers=auth_org_a["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == auth_org_a["user"]["email"]
    assert data["org"]["id"] == auth_org_a["org"]["id"]
    assert data["role"] == "owner"
