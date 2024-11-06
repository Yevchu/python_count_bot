import os
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # Переконайтесь, що змінна називається DATABASE_URL

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
    unique_mebmer_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

class PotentialAdmin(Base):
    __tablename__ = "potential_admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    requested_at = Column(DateTime, default=func.now())

    @staticmethod
    def clean_old_potential_admins(session):
        expiry_time = datetime.now(datetime.timezone.utc) - timedelta(hours=24)
        session.querry(PotentialAdmin).filter(PotentialAdmin.requested_at < expiry_time).delete()
        session.commit()

def add_super_admin_if_not_exist(super_admin_id):
    session = SessionLocal()
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
    finally:
        session.close()

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    init_db()