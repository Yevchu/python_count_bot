import pytest
from services.group_service import GroupService
from sqlalchemy.orm import Session
from db_config import UserGroup, Group
import threading
import random
import logging
from test_db import TestSessionLocal, create_test_database, drop_test_database
from concurrent.futures import ThreadPoolExecutor


# Налаштування логування
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    """Фікстура для налаштування тестової бази."""
    logger.info("Створення тестової бази даних...")
    create_test_database()
    yield
    logger.info("Видалення тестової бази даних...")
    drop_test_database()

@pytest.fixture
def db_session():
    """Фікстура для створення сесії тестової бази."""
    logger.info("Створення нової сесії для тесту...")
    session = TestSessionLocal()
    try:
        yield session
    finally:
        logger.info("Закриття сесії...")
        session.close()

@pytest.fixture
def test_groups():
    """Створює набір груп для тестування."""
    groups = [{"group_id": i, "group_name": f"Group {i}"} for i in range(1, 3)]  # 50 груп
    logger.info(f"Згенеровано {len(groups)} тестових груп.")
    return groups

@pytest.fixture
def test_users():
    """Створює набір користувачів для тестування."""
    users = [i for i in range(1, 11)]  # Генерує 100 користувачів
    logger.info(f"Згенеровано {len(users)} тестових користувачів.")
    return users

def add_unique_member_in_thread(group_id, user_id):
    """Функція для додавання унікального учасника в окремому потоці."""
    session = TestSessionLocal()  # Окрема сесія для потоку
    group_service = GroupService(session)
    logger.info(f"[Thread-{threading.get_ident()}] Початок додавання користувача {user_id} до групи {group_id}.")
    try:
        group = group_service.get_or_create_group(group_id=group_id, group_name=f"Group {group_id}")
        result = group_service.add_unique_member(group, user_id)
        if result:
            logger.info(f"[Thread-{threading.get_ident()}] Користувача {user_id} успішно додано до групи {group_id}.")
        else:
            logger.warning(f"[Thread-{threading.get_ident()}] Користувач {user_id} вже є у групі {group_id}.")
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"[Thread-{threading.get_ident()}] Помилка при додаванні користувача {user_id} до групи {group_id}: {e}")
    finally:
        session.close()

def test_stress_test_unique_members(test_groups, test_users):
    logger.info("Початок стрес-тесту...")
    threads = []

    # Підготовка груп у базі
    session = TestSessionLocal()
    group_service = GroupService(session)
    logger.info("Підготовка тестових груп у базі даних...")
    for group_data in test_groups:
        group_service.get_or_create_group(group_id=group_data["group_id"], group_name=group_data["group_name"])
    session.commit()
    session.close()
    logger.info("Тестові групи успішно додані до бази даних.")

    # Використання потоків для додавання користувачів
    with ThreadPoolExecutor(max_workers=10) as executor:
        for user_id in test_users:
            random_group = random.choice(test_groups)
            group_id = random_group["group_id"]
            executor.submit(add_unique_member_in_thread, group_id, user_id)

    logger.info("Усі потоки завершили роботу.")

    # Перевірка кількості користувачів у базі
    session = TestSessionLocal()
    try:
        for group_data in test_groups:
                group_id = group_data["group_id"]
                group = group_service.get_group_by_identifier(session, group_id)
                assert group is not None, f"Група з ID {group_id} повинна існувати"
                logger.info(f"Група {group_id}: {group.unique_members_count} унікальних учасників.")
                logger.info("Стрес-тест успішно завершено.")
    finally:
        session.close()
    logger.info("Стрес-тест успішно завершено.")
