from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# ponytail: SQLite for dev, PostgreSQL for production
if "sqlite" in settings.database_url:
    engine = create_async_engine(
        settings.database_url, echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        settings.database_url, echo=False, pool_size=10, max_overflow=20,
    )

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_database():
    from app.infrastructure.persistence.models import Base
    from app.domain.user.auth import User
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose():
    await engine.dispose()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
