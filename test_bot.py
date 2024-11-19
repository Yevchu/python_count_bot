import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update, Chat, User
from telegram.ext import ContextTypes
from group import new_member
from test_db import TestSessionLocal, create_test_database, drop_test_database
from services.group_service import GroupService

@pytest.fixture(scope="session", autouse=True)
def setup_and_teardown_database():
    # Створення тестової бази
    create_test_database()
    yield
    # Видалення тестової бази після завершення
    drop_test_database()

@pytest.mark.asyncio
@patch("telegram.Bot.get_chat_member_count", new_callable=AsyncMock)
@patch("telegram.Bot.get_chat_member", new_callable=AsyncMock)
async def test_new_member_with_mocked_telegram_api(mock_get_chat_member, mock_get_chat_member_count):
    # Емуляція відповіді Telegram API
    mock_get_chat_member_count.return_value = 5
    mock_get_chat_member.return_value = AsyncMock(
        user=User(id=12345, first_name="Test", is_bot=False),
        status="member",
    )

    # Емуляція Telegram-об'єктів
    mock_chat = Chat(id=-100123456789, type="group", title="Test Group")
    mock_update = AsyncMock(spec=Update)
    mock_update.effective_chat = mock_chat
    mock_update.message.new_chat_members = [
        User(id=12345, first_name="Test", is_bot=False),
        User(id=67890, first_name="Another", is_bot=False),
        User(id=12342, first_name="Test", is_bot=False),
        User(id=67892, first_name="Another", is_bot=False),
        User(id=12343, first_name="Test", is_bot=False),
        User(id=67893, first_name="Another", is_bot=False),
        User(id=12344, first_name="Test", is_bot=False),
        User(id=67894, first_name="Another", is_bot=False),
        User(id=123455, first_name="Test", is_bot=False),
        User(id=67895, first_name="Another", is_bot=False),
        User(id=12346, first_name="Test", is_bot=False),
        User(id=67896, first_name="Another", is_bot=False),
        User(id=12347, first_name="Test", is_bot=False),
        User(id=67897, first_name="Another", is_bot=False),
        User(id=12348, first_name="Test", is_bot=False),
        User(id=67898, first_name="Another", is_bot=False),
        User(id=12349, first_name="Test", is_bot=False),
        User(id=67899, first_name="Another", is_bot=False),
        User(id=123451, first_name="Test", is_bot=False),
        User(id=678901, first_name="Another", is_bot=False),
        User(id=123452, first_name="Test", is_bot=False),
        User(id=678902, first_name="Another", is_bot=False),
        User(id=123453, first_name="Test", is_bot=False),
        User(id=678903, first_name="Another", is_bot=False),
        User(id=123454, first_name="Test", is_bot=False),
        User(id=678904, first_name="Another", is_bot=False),

    ]

    mock_context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_context.bot.id = 98765

    with TestSessionLocal() as session:
        group_service = GroupService(session)

        # Виклик функції
        await new_member(mock_update, mock_context)

        # Перевірка результатів у базі
        group = group_service.get_group_by_identifier(session, mock_chat.id)
        assert group is not None, "Група не була додана до бази даних"
        assert group.unique_members_count == 2, "Лічильник унікальних учасників неправильний"

        for user in mock_update.message.new_chat_members:
            db_user = group_service.get_user(user_id=user.id, group_id=mock_chat.id)
            assert db_user is not None, f"Користувач ID {user.id} не був доданий до бази даних"
