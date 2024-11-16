import logging
from db_config import Group, UserGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import Optional, Union
from services.tg_api_service import TelegramAPI

logging.basicConfig(
    level=logging.INFO,  # Можна змінити на DEBUG для більш детального логування
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class GroupService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_user(self, user_id: int, group_id: int) -> Optional[UserGroup]:
        user = UserGroup(user_id=user_id, group_id=group_id)
        self.session.add(user)
        try:
            await self.session.commit()
            return user
        except IntegrityError:
            await self.session.rollback()
            return None
    
    async def get_user(self, user_id: int, group_id: int) -> UserGroup:
        user = await self.session.execute(
            select(UserGroup).filter_by(user_id=user_id, group_id=group_id).with_for_update()
        )
        return user.scalar()

    async def add_unique_member(self, group: Group, user_id: int) -> bool:
        """
        Додає унікального учасника до групи. Якщо користувач вже існує, повертає False.
        """
        async with self.session.begin_nested():  # Використання вкладеної транзакції
            try:
                # Перевірка, чи користувач вже існує
                existing_user = await self.session.execute(
                    select(UserGroup).filter_by(user_id=user_id, group_id=group.group_id)
                )
                if existing_user.scalar():
                    logging.info(f"Користувач {user_id} вже існує в групі {group.group_id}")
                    return False  # Користувач вже доданий

                # Додавання нового користувача
                new_user_group = UserGroup(user_id=user_id, group_id=group.group_id)
                self.session.add(new_user_group)
                await self.session.flush()  # Збереження без commit

                # Оновлення кількості унікальних користувачів
                group.unique_members_count += 1
                self.session.add(group)  # Додаємо зміни в групу
                await self.session.commit()  # Збереження змін у базі даних

                logging.info(f"Користувач {user_id} успішно доданий до групи {group.group_id}")
                return True
            except IntegrityError as e:
                # Обробка помилки унікальності
                await self.session.rollback()
                logging.error(f"Помилка додавання користувача {user_id} до групи {group.group_id}: {e}")
                return False
            except Exception as e:
                # Загальна обробка виключень
                await self.session.rollback()
                logging.error(f"Невідома помилка: {e}")
                return False

    @staticmethod
    async def get_group_by_identifier(session: AsyncSession, group_identifier: Union[str, int]) -> Optional[Group]:
        if isinstance(group_identifier, int):
            result = await session.execute(
                select(Group).filter_by(group_id=group_identifier)
            )
        else:
            result = await session.execute(
                select(Group).filter_by(group_name=group_identifier)
            )
        return result.scalar()

    @staticmethod
    async def get_active_groups(session: AsyncSession) -> list:
        result = await session.execute(
            select(Group).filter_by(is_active=True)
        )
        return result.scalars().all()
        
    async def create_group(self, group_id: int, group_name: str) -> Group:
        group = Group(group_id=group_id, group_name=group_name, unique_members_count=0)
        self.session.add(group)
        try:
            await self.session.commit()
            await self.session.refresh(group)
            return group
        except IntegrityError:
            await self.session.rollback()
            raise

    async def get_or_create_group(self, group_id: int, group_name: str) -> Group:
        group = await self.get_group_by_identifier(self.session, group_id)
        if not group:
            group = await self.create_group(group_id, group_name)
        return group
    
    async def delete_group(self, group_identifier: Union[str, int]) -> str:
        group = await self.get_group_by_identifier(self.session, group_identifier)
        if not group:
            return "Такої групи не було знайдено."
        try:
            await self.session.delete(group)
            await self.session.commit()
            return f"Групу {group.group_name} було видаленно."
        except IntegrityError:
            await self.session.rollback()
            return "Сталася помилка при видаленні групи"

class GroupSyncService:
    def __init__(self, session: AsyncSession, chat_api: TelegramAPI):
        self.session = session
        self.chat_api = chat_api

    async def sync_members(self, group_id: int) -> None:
        try:
            group_service = GroupService(self.session)
            group = await group_service.get_group_by_identifier(self.session, group_id)
            if not group:
                raise ValueError(f"Групу з ID {group_id} не знайдено")
            
            telegram_members = await self.chat_api.get_members(group_id)
            for member in telegram_members:
                if not await group_service.get_user(member.user.id, group_id):
                    await group_service.add_unique_member(group, member.user.id)

            group.unique_members_count = max(group.unique_members_count, len(telegram_members))
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logging.error(f"Помилка синхронізації для групи {group_id}: {str(e)}")