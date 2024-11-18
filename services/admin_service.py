from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import Optional
from db_config import Admin, PotentialAdmin

class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_admin_by_id(self, user_id: int) -> Optional[Admin]:
        result = await self.session.execute(
            select(Admin).filter_by(user_id=user_id)
        )
        return result.scalars().first()
    
    async def get_admin_by_username(self, username: str) -> Optional[Admin]:
        result = await self.session.execute(
            select(Admin).filter_by(username=username)
        )
        return result.scalars().first()
    
    async def get_potential_admin_by_username(self, username: str) -> Optional[PotentialAdmin]:
        result = await self.session.execute(
            select(PotentialAdmin).filter_by(username=username)
        )
        return result.scalars().first()
    
    async def add_admin(self, user_id: int, username: str = None) -> bool:
        new_admin = Admin(user_id=user_id, username=username, is_super_admin=False)
        try:
            self.session.add(new_admin)
            await self.session.commit()
            return True
        except IntegrityError:
            await self.session.rollback()
            return False

    async def remove_admin_by_id(self, user_id: int) -> str:
        admin = await self.get_admin_by_id(user_id=user_id)
        if not admin:
            return "Адміністратора з таким ID не знайдено."
        await self.session.delete(admin)
        await self.session.commit()
        return "Адміністратора успішно видалено."

    async def get_super_admin_by_id(self, user_id: int) -> Optional[Admin]:
        result = await self.session.execute(
            select(Admin).filter_by(user_id=user_id, is_super_admin=True)
        )
        return result.scalars().first()
        
    async def add_super_admin(self, user_id: int) -> str:
        existing_admin = await self.get_admin_by_id(user_id)
        if existing_admin:
            if existing_admin.is_super_admin:
                return "Користувач вже є суперадміністратором."
            existing_admin.is_super_admin = True
            await self.session.commit()
            return "Адміністратора було успішно призначено суперадміністратором."
    
    async def new_super_admin(self, user_id: int, username: Optional[str] = None) -> str:
        new_super_admin = Admin(user_id=user_id, username=username, is_super_admin=True)
        self.session.add(new_super_admin)
        await self.session.commit()
        return "Новий суперадміністратор доданий."

    async def remove_super_admin(self, user_id: int) -> str:
        result = await self.session.execute(
            select(Admin).filter_by(user_id=user_id, is_super_admin=True)
        )
        super_admin = result.scalars().first()
        if not super_admin:
            return "Суперадміністратора з таким ID не знайдено."
        await self.session.delete(super_admin)
        await self.session.commit()
        return "Суперадміністратора успішно видалено."

