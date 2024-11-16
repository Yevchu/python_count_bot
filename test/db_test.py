from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData
from db_config import Base

# URL тестової бази даних
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:123456@localhost:5432/postgres"

# Налаштування асинхронного двигуна для тестової бази
test_engine = create_async_engine(TEST_DATABASE_URL, future=True, echo=True)

# Сесія для тестової бази
TestAsyncSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Метадані для взаємодії з базою
test_metadata = MetaData()


# Функція для створення таблиць у тестовій базі
async def create_test_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Функція для видалення таблиць у тестовій базі
async def drop_test_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
