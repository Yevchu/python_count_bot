import os
from sqlalchemy import create_engine, ForeignKey, UniqueConstraint, Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    max_member_count = Column(Integer, default=0)

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
    def clean_old_potential_admins(session):
        expiry_time = datetime.now(timezone.utc) - timedelta(hours=24)
        session.query(PotentialAdmin).filter(PotentialAdmin.requested_at < expiry_time).delete()
        session.flush()
        session.commit()

def add_super_admin_if_not_exist(super_admin_id):
    with SessionLocal() as session:
        try:
            admin = session.query(Admin).filter_by(user_id=super_admin_id).first()
            if not admin:
                super_admin = Admin(user_id=super_admin_id, is_super_admin=True)
                session.add(super_admin)
                session.commit()
                print(f"Супер адміністратора з ID {super_admin_id} додано в базу даних.")
            else:
                print(f"Супер адміністратор з ID {super_admin_id} вже існує в базі даних.")
        except IntegrityError:
            session.rollback()
            print("Помилка: не вдалося додати супер адміністратора.")

def init_db():
    Base.metadata.create_all(bind=engine)
