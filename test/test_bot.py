import pytest
import asyncio
from random import randint
from unittest.mock import AsyncMock, MagicMock, patch
from services.group_service import GroupSyncService, GroupService
from services.tg_api_service import TelegramAPI
from db_config import AsyncSessionLocal, Group
from db_test import create_test_database, drop_test_database, TestAsyncSessionLocal

# @pytest.fixture(scope="session", autouse=True)
# async def setup_test_database():
#     await create_test_database()
#     yield
#     await drop_test_database()

# # Фікстура для надання ізольованої сесії
# @pytest.fixture
# async def test_session():
#     async with TestAsyncSessionLocal() as session:
#         async with session.begin_nested():
#             yield session
#         await session.rollback()

@pytest.mark.asyncio
async def test_sync_members():
    # Мокаємо TelegramAPI
    mock_chat_api = AsyncMock()
    mock_chat_api.get_members = AsyncMock(return_value=[
        MagicMock(user=MagicMock(id=1)),
        MagicMock(user=MagicMock(id=2)),
    ])
    
    # Мокаємо сесію та GroupService
    mock_session = AsyncMock()
    mock_group = MagicMock(group_id=-100123456789, unique_members_count=0)
    
    mock_group_service = AsyncMock()
    mock_group_service.get_group_by_identifier = AsyncMock(return_value=mock_group)
    mock_group_service.get_user = AsyncMock(return_value=None)
    mock_group_service.add_unique_member = AsyncMock()
    
    # Інтегруємо моки через патч
    with patch("services.group_service.GroupService", return_value=mock_group_service):
        group_sync_service = GroupSyncService(mock_session, mock_chat_api)
        group_id = -100123456789

        # Викликаємо функцію
        await group_sync_service.sync_members(group_id)

        # Перевіряємо виклики
        mock_chat_api.get_members.assert_called_once_with(group_id)
        mock_group_service.get_group_by_identifier.assert_called_once_with(mock_session, group_id)
        assert mock_group_service.add_unique_member.call_count == 2
        assert mock_group.unique_members_count == 2
        mock_session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_add_unique_member():
    async with AsyncSessionLocal() as session:
        group_service = GroupService(session)

        group_id = -100123456789
        user_id = 12345

        # Створення групи
        group = await group_service.get_group_by_identifier(session, group_id)
        if not group:
            group = Group(group_id=group_id, group_name="Test Group", unique_members_count=0)
            session.add(group)
            await session.commit()
            await session.refresh(group)

        # Додавання нового учасника
        result = await group_service.add_unique_member(group, user_id)
        assert result is True, "Додавання нового учасника повинно бути успішним"

        # Повторне додавання того ж учасника
        result = await group_service.add_unique_member(group, user_id)
        assert result is False, "Повторне додавання того ж учасника повинно провалитися"

        # Перевірка унікальної кількості учасників
        assert group.unique_members_count == 1, "Кількість унікальних учасників повинна бути 1"


@pytest.mark.asyncio
async def test_database_load():
    async def add_mock_member(group_id, user_id):
        async with AsyncSessionLocal() as session:
            group_service = GroupService(session)
            group = await group_service.get_group_by_identifier(session, group_id)
            if not group:
                group = Group(group_id=group_id, group_name="Test Group", unique_members_count=0)
                session.add(group)
                await session.commit()
                await session.refresh(group)
            await group_service.add_unique_member(group, user_id)

    # Конфігурація навантаження
    group_id = -100123456789
    num_tasks = 10  # Зменшено для тестування
    user_ids = [randint(1, 10000) for _ in range(num_tasks)]

    # Створюємо задачі для навантаження
    tasks = [add_mock_member(group_id, user_id) for user_id in user_ids]

    # Виконуємо задачі паралельно
    await asyncio.gather(*tasks)

    # Перевіряємо результат
    async with AsyncSessionLocal() as session:
        group_service = GroupService(session)
        group = await group_service.get_group_by_identifier(session, group_id)
        assert group.unique_members_count == len(set(user_ids)), \
            f"Очікувалось: {len(set(user_ids))}, отримано: {group.unique_members_count}"

