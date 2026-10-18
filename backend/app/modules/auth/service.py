"""Business logic service for authentication, registration, login, and token rotation."""

import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.models import MembershipRole
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    OrgResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuthRepository(session)
        self.settings = get_settings()

    async def register(self, req: RegisterRequest) -> TokenResponse:
        existing = await self.repo.get_user_by_email(req.email)
        if existing:
            raise ConflictError("EMAIL_ALREADY_EXISTS", "A user with this email already exists")

        # 1. Create User with Argon2 hash
        pw_hash = hash_password(req.password)
        user = await self.repo.create_user(req.email, pw_hash, req.full_name)

        # 2. Create Personal Organization
        org_name = (
            req.org_name.strip()
            if req.org_name and req.org_name.strip()
            else f"{req.full_name}'s Studio"
        )
        base_slug = slugify(org_name)
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        org = await self.repo.create_organization(org_name, slug)

        # 3. Create Owner Membership
        await self.repo.create_membership(user.id, org.id, MembershipRole.OWNER)

        # 4. Generate Access and Refresh Tokens
        access_token = create_access_token(
            subject=str(user.id),
            org_id=str(org.id),
            role=MembershipRole.OWNER.value,
        )

        raw_refresh_token = generate_secure_token()
        refresh_expires = datetime.now(UTC) + timedelta(
            days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.repo.save_refresh_token(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=refresh_expires,
        )

        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
            org=OrgResponse.model_validate(org),
        )

    async def login(self, req: LoginRequest) -> TokenResponse:
        user = await self.repo.get_user_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise UnauthorizedError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS",
            )

        membership_tuple = await self.repo.get_user_primary_membership(user.id)
        if not membership_tuple:
            raise UnauthorizedError("User has no active organization membership")

        membership, org = membership_tuple

        access_token = create_access_token(
            subject=str(user.id),
            org_id=str(org.id),
            role=membership.role.value,
        )

        raw_refresh_token = generate_secure_token()
        refresh_expires = datetime.now(UTC) + timedelta(
            days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.repo.save_refresh_token(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=refresh_expires,
        )

        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
            org=OrgResponse.model_validate(org),
        )

    async def refresh_tokens(self, req: RefreshRequest) -> TokenResponse:
        t_hash = hash_token(req.refresh_token)
        token_record = await self.repo.get_refresh_token(t_hash)

        if not token_record or token_record.is_revoked:
            raise UnauthorizedError(
                message="Refresh token is invalid or has been revoked",
                code="INVALID_REFRESH_TOKEN",
            )

        now = datetime.now(UTC)
        if token_record.expires_at < now:
            raise UnauthorizedError(
                message="Refresh token has expired",
                code="INVALID_REFRESH_TOKEN",
            )

        # Token Rotation: Revoke previous token immediately
        await self.repo.revoke_refresh_token(token_record)

        user = await self.repo.get_user_by_id(token_record.user_id)
        if not user:
            raise UnauthorizedError("User no longer exists")

        membership_tuple = await self.repo.get_user_primary_membership(user.id)
        if not membership_tuple:
            raise UnauthorizedError("User has no active organization membership")

        membership, org = membership_tuple

        # Generate new tokens
        new_access_token = create_access_token(
            subject=str(user.id),
            org_id=str(org.id),
            role=membership.role.value,
        )

        new_raw_refresh_token = generate_secure_token()
        refresh_expires = now + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.repo.save_refresh_token(
            user_id=user.id,
            token_hash=hash_token(new_raw_refresh_token),
            expires_at=refresh_expires,
        )

        await self.session.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
            org=OrgResponse.model_validate(org),
        )

    async def logout(self, req: LogoutRequest) -> None:
        t_hash = hash_token(req.refresh_token)
        token_record = await self.repo.get_refresh_token(t_hash)
        if token_record and not token_record.is_revoked:
            await self.repo.revoke_refresh_token(token_record)
            await self.session.commit()
