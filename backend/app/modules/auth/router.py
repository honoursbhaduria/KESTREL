"""Authentication router endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.dependencies import AuthContext, get_current_auth_context
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    OrgResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    service = AuthService(session)
    return await service.register(req)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    service = AuthService(session)
    return await service.login(req)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    service = AuthService(session)
    return await service.refresh_tokens(req)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    req: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    service = AuthService(session)
    await service.logout(req)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=MeResponse)
async def get_me(
    auth: AuthContext = Depends(get_current_auth_context),
) -> MeResponse:
    return MeResponse(
        user=UserResponse.model_validate(auth.user),
        org=OrgResponse.model_validate(auth.org),
        role=auth.role,
    )
