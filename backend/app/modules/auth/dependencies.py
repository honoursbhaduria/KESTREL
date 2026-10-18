"""FastAPI dependency for JWT authentication and multi-tenant authorization context."""

import uuid
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.modules.auth.models import Membership, Organization, User

security = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    org: Organization
    role: str


async def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> AuthContext:
    if not credentials or not credentials.credentials:
        raise UnauthorizedError("Missing or invalid authorization header")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception as e:
        raise UnauthorizedError(f"Invalid authentication token: {e}") from e

    try:
        user_id = uuid.UUID(payload["sub"])
        org_id = uuid.UUID(payload["org_id"])
    except (ValueError, KeyError) as e:
        raise UnauthorizedError("Malformed token payload") from e

    # Fetch user, org, and verify membership
    stmt = (
        select(User, Organization, Membership)
        .join(Membership, Membership.user_id == User.id)
        .join(Organization, Membership.org_id == Organization.id)
        .where(
            User.id == user_id,
            Organization.id == org_id,
            User.is_active.is_(True),
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        raise UnauthorizedError("Invalid user or organization context")

    user, org, membership = row
    return AuthContext(user=user, org=org, role=membership.role.value)
