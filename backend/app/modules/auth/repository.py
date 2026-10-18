"""Database repository for users, organizations, memberships, and refresh tokens."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Membership, MembershipRole, Organization, RefreshToken, User


class AuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower().strip())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_user(self, email: str, password_hash: str, full_name: str) -> User:
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash,
            full_name=full_name.strip(),
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def create_organization(self, name: str, slug: str) -> Organization:
        org = Organization(name=name.strip(), slug=slug.strip())
        self.session.add(org)
        await self.session.flush()
        return org

    async def create_membership(
        self, user_id: uuid.UUID, org_id: uuid.UUID, role: MembershipRole
    ) -> Membership:
        membership = Membership(user_id=user_id, org_id=org_id, role=role)
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def get_user_membership(self, user_id: uuid.UUID, org_id: uuid.UUID) -> Membership | None:
        stmt = select(Membership).where(Membership.user_id == user_id, Membership.org_id == org_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_primary_membership(
        self, user_id: uuid.UUID
    ) -> tuple[Membership, Organization] | None:
        stmt = (
            select(Membership, Organization)
            .join(Organization, Membership.org_id == Organization.id)
            .where(Membership.user_id == user_id)
            .order_by(Membership.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return res.first()

    async def save_refresh_token(
        self, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token_record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.session.add(token_record)
        await self.session.flush()
        return token_record

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def revoke_refresh_token(self, token_record: RefreshToken) -> None:
        token_record.is_revoked = True
        await self.session.flush()
