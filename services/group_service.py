from db_config import Group, SessionLocal
from sqlalchemy.orm import Session
from typing import Optional, Union

class GroupService:
    def __init__(self, session: Session):
        self.session = session

    def add_unique_member(self, group: Group, user_id: int) -> bool:
        if user_id not in group.unique_users:
            group.unique_users.add(user_id)
            group.unique_members_count += 1
            self.session.commit()
            return True
        return False
    
    @staticmethod
    def get_group_by_identifier(session: Session, group_identifier: str) -> Optional[Group]:
        try:
            group_id = int(group_identifier)
            group = session.query(Group).filter_by(group_id=group_id, is_active=True).first()
        except ValueError:
            group = session.query(Group).filter_by(group_name=group_identifier, is_active=True).first()
    
        return group

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

    def get_or_creat_group(self, group_id: int, group_name: str) -> Group:
        group = self.get_group_by_identifier(self.session, str(group_id))
        if not group:
            group = self.create_group(group_id, group_name)
            self.session.add(group)
            self.session.commit()
        return group
    
    def delete_group(self, group_identifier: Union[str, int]) -> str:
        group = self.get_group_by_identifier(self.session, group_identifier)
        if not group:
            return "Такої групи не було знайдено."
        
        self.session.delete(group)
        self.session.commit()
        return "Групу було видаленно."