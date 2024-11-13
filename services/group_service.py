from db_config import Group, SessionLocal, UserGroup
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Union

class GroupService:
    def __init__(self, session: Session):
        self.session = session

    def add_unique_member(self, group: Group, user_id: int) -> bool:
        existing_user = self.session.query(UserGroup).filter_by(user_id=user_id, group_id=group.id).first()
        
        if existing_user:
            return "Користувач вже був доданий раніше"

        new_user_group = UserGroup(user_id=user_id, group_id=group.id)
        self.session.add(new_user_group)
        group.unique_members_count += 1
        return "Користувача додано до групи."
    
    @staticmethod
    def get_group_by_identifier(session, group_identifier: Union[str, int]) -> Optional[Group]:
        if isinstance(group_identifier, int):
            return session.query(Group).filter_by(group_id=group_identifier).first()
        else: 
            return session.query(Group).filter_by(group_name=group_identifier).first()

    @staticmethod
    def get_active_groups() -> list:
        with SessionLocal() as session:
            active_groups = session.query(Group).filter_by(is_active=True).all()
            return active_groups
        
    def create_group(self, group_id: int, group_name: str) -> Group:
        group = Group(group_id=group_id, group_name=group_name, unique_members_count=0)
        self.session.add(group)
        self.session.commit()
        return group

    def get_or_create_group(self, group_id: int, group_name: str) -> Group:
        group = self.get_group_by_identifier(self.session, group_id)
        if not group:
            group = self.create_group(group_id, group_name)
            self.session.commit()
        return group
    
    def delete_group(self, group_identifier: Union[str, int]) -> str:
        group = self.get_group_by_identifier(self.session, group_identifier)
        if not group:
            return "Такої групи не було знайдено."
        try:
            self.session.delete(group)
            self.session.commit()
            return f"Групу {group.group_name} було видаленно."
        except IntegrityError:
            self.session.rollback()
            return "Сталася помилка при видаленні групи"

