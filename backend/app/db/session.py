"""Async SQLAlchemy session factory and dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

if settings.ENVIRONMENT == "testing":
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG and settings.ENVIRONMENT == "development",
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
