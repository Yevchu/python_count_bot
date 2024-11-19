from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from db_config import Admin, PotentialAdmin
class AdminService:
    def __init__(self, session: Session):
        self.session = session
    def get_admin_by_id(self, user_id: int) -> Admin:
        return self.session.query(Admin).filter_by(user_id=user_id).first()
    
    def get_admin_by_username(self, username: int) -> Admin:
        return self.session.query(Admin).filter_by(username=username).first()
    
    def get_potential_admin_by_username(self, username: str) -> PotentialAdmin:
        return self.session.query(PotentialAdmin).filter_by(username=username).first()
    
    def add_admin(self, user_id: int, username: str = None) -> bool:
        new_admin = Admin(user_id=user_id, username=username, is_super_admin=False)
        try:
            self.session.add(new_admin)
            self.session.commit()
            return True
        except IntegrityError:
            self.session.rollback()
            return False
    def remove_admin_by_id(self, user_id: int) -> str:
        admin = self.get_admin_by_id(user_id=user_id)
        if not admin:
            return "Aдміністратора з таким ID не знайдено."
        self.session.delete(admin)
        self.session.commit()
        return "Aдміністратора успішно видалено."
    def get_super_admin_by_id(self, user_id: int) -> Admin:
        return self.session.query(Admin).filter_by(user_id=user_id, is_super_admin=True).first()
        
    def add_super_admin(self, user_id: int) -> str:
        existing_admin = self.get_admin_by_id(user_id)
        if existing_admin:
            if existing_admin.is_super_admin:
                return "Користувач вже є суперадміністратором."
            existing_admin.is_super_admin = True
            self.session.commit()
            return "Адміністратора було успішно призначено суперадміністратором."
    
    def new_super_admin(self, user_id: int, username: Optional[str] = None) -> str:
        new_super_admin = self.add_admin(user_id=user_id, username=username, is_super_admin=True)
        self.session.add(new_super_admin)
        self.session.commit()
        return "Новий суперадміністратор доданий."
    def remove_super_admin(self, user_id: int) -> str:
        super_admin = self.session.query(Admin).filter_by(user_id=user_id, is_super_admin=True).first()
        if not super_admin:
            return "Суперадміністратора з таким ID не знайдено."
        self.session.delete(super_admin)
        self.session.commit()
        return "Суперадміністратора успішно видалено."