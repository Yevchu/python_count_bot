from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_config import Base

# URL тестової бази даних
TEST_DATABASE_URL = "postgresql://root:root@localhost:5432/test_db"

# Налаштування синхронного двигуна для тестової бази
test_engine = create_engine(TEST_DATABASE_URL)

# Сесія для тестової бази
TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)

# Функція для створення таблиць у тестовій базі
def create_test_database():
    Base.metadata.create_all(bind=test_engine)

# Функція для видалення таблиць у тестовій базі
def drop_test_database():
    Base.metadata.drop_all(bind=test_engine)
