import os
import logging
from sqlalchemy import ForeignKey, UniqueConstraint, Column, Integer, BigInteger, String, Boolean, DateTime, delete, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    is_super_admin = Column(Boolean, default=False)

class Group(Base): 
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(BigInteger, unique=True, nullable=False)
    group_name = Column(String, nullable=False)
    added_at = Column(DateTime, default=func.now())
    unique_members_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    unique_users = relationship("UserGroup", back_populates="group", cascade='all, delete')

class UserGroup(Base):
    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False)
    group_id = Column(BigInteger, ForeignKey('groups.group_id'), nullable=False)
    
    __table_args__ = (UniqueConstraint('user_id', 'group_id', name='_user_group_uc'),)

    group = relationship("Group", back_populates="unique_users")


class PotentialAdmin(Base):
    __tablename__ = "potential_admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    requested_at = Column(DateTime, default=func.now())

    @staticmethod
    async def clean_old_potential_admins(session: AsyncSession):
        expiry_time = datetime.now(timezone.utc) - timedelta(hours=24)
        async with session.begin():  
            await session.execute(
                delete(PotentialAdmin).where(PotentialAdmin.requested_at < expiry_time)
            )

async def add_super_admin_if_not_exist(super_admin_id):
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Admin).filter_by(user_id=super_admin_id)
            )
            admin = result.scalars().first()

            if not admin:
                super_admin = Admin(user_id=super_admin_id, is_super_admin=True)
                session.add(super_admin)
                await session.commit()  
                logger.info(f"Супер адміністратора з ID {super_admin_id} додано в базу даних.")
            else:
                logger.info(f"Супер адміністратор з ID {super_admin_id} вже існує в базі даних.")
        except IntegrityError:
            await session.rollback()  
            logger.error("Помилка: не вдалося додати супер адміністратора через порушення цілісності даних.")
        except Exception as e:
            await session.rollback()
            logger.exception(f"Непередбачена помилка при додаванні супер адміністратора: {e}")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
