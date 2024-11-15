from db_config import Group, AsyncSessionLocal, UserGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import Optional, Union

class GroupService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_user(self, user_id: int, group_id: int) -> Optional[UserGroup]:
        user = UserGroup(user_id=user_id, group_id=group_id)
        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            return None
    
    async def get_user(self, user_id: int, group_id: int) -> UserGroup:
        user = await self.session.execute(
            select(UserGroup).filter_by(user_id=user_id, group_id=group_id)
        )
        return user.scalar()

    async def add_unique_member(self, group: Group, user_id: int) -> bool:
        new_user_group = await self.add_user(user_id=user_id, group_id=group.group_id)
        if new_user_group:
            group.unique_members_count += 1
            self.session.add(group)
            try:
                await self.session.commit()
                return True
            except Exception:
                await self.session.rollback()
                return False
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

