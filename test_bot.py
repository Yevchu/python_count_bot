import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, User, Chat
from telegram.ext import ContextTypes
from db_config import Group
from services.group_service import GroupService
from group import new_member
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_new_member():
    # Тестові дані
    user_id = 12345
    group_id = -100123456789
    group_name = "Test Group"
    new_user = User(id=user_id, is_bot=False, first_name="TestUser")
    chat = Chat(id=group_id, type="group", title=group_name)

    # Мокаємо Update
    update = Update(
        update_id=1,
        message=AsyncMock(chat=chat, new_chat_members=[new_user])
    )

    # Мокаємо Application і Context
    context = ContextTypes.DEFAULT_TYPE(application=AsyncMock())

    # Мокаємо сесію та сервіс груп
    mock_session_instance = AsyncMock(spec=AsyncSession)
    mock_group_service = MagicMock(spec=GroupService)
    mock_group_service.get_or_create_group = AsyncMock(
        return_value=Group(group_id=group_id, group_name=group_name, unique_members_count=0)
    )
    mock_group_service.add_unique_member = AsyncMock(return_value=True)

    # Патчимо AsyncSessionLocal і GroupService
    with patch("group.AsyncSessionLocal", return_value=mock_session_instance) as mock_session_local, \
         patch("group.GroupService", return_value=mock_group_service):

        # Виклик функції
        await new_member(update, context)

        # Перевірка, що `get_or_create_group` викликано з правильними аргументами
        mock_group_service.get_or_create_group.assert_called_once_with(group_id, group_name)

        # Перевірка, що `add_unique_member` викликано з правильними аргументами
        mock_group_service.add_unique_member.assert_called_once_with(
            mock_group_service.get_or_create_group.return_value, user_id
        )

        # Перевірка, що `commit` викликано
        mock_session_instance.commit.assert_awaited_once()
