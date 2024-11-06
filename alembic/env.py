import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv
from db_config import Base  # Імпорт бази для метаданих

# Завантаження змінних середовища
load_dotenv()

# Налаштування Alembic Config
config = context.config

# Налаштування логування
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Отримання URL бази даних із середовища
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Метадані для моделей
target_metadata = Base.metadata  # Використовуємо Base.metadata з db_config.py

def run_migrations_offline():
    """Запуск міграцій в 'offline' режимі."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Запуск міграцій в 'online' режимі."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

# Вибір режиму міграції в залежності від контексту
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
