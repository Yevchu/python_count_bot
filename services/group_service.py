import logging
from db_config import Group, SessionLocal, UserGroup
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Union

logging.basicConfig(
    level=logging.DEBUG,  # Можна змінити на DEBUG для більш детального логування
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GroupService:
    def __init__(self, session: Session):
        self.session = session

    def add_user(self, user_id: int, group_id: int) -> UserGroup:
        """Додає користувача до бази."""
        logger.debug(f"Виклик add_user з параметрами: user_id={user_id}, group_id={group_id}")
        user = UserGroup(user_id=user_id, group_id=group_id)
        self.session.add(user)
        logger.debug(f"Користувача {user_id} додано до сесії для групи {group_id}")
        return user

    def get_user(self, user_id: int, group_id: int) -> UserGroup:
        """Отримує користувача за ID."""
        logger.debug(f"Виклик get_user з параметрами: user_id={user_id}, group_id={group_id}")
        user = self.session.query(UserGroup).filter_by(user_id=user_id, group_id=group_id).first()
        if user:
            logger.debug(f"Користувача знайдено: user_id={user_id}, group_id={group_id}")
        else:
            logger.debug(f"Користувача не знайдено: user_id={user_id}, group_id={group_id}")
        return user

    def add_unique_member(self, group: Group, user_id: int) -> bool:
        """Додає унікального учасника до групи."""
        logger.debug(f"Виклик add_unique_member для групи {group.group_id} з user_id={user_id}")

        # Перевірка існуючого користувача
        existing_user = self.get_user(user_id=user_id, group_id=group.group_id)
        if existing_user:
            logger.info(f"Користувач {user_id} вже існує в групі {group.group_id}")
            return False

        try:
            # Додавання нового користувача
            self.add_user(user_id=user_id, group_id=group.group_id)

            # Атомарне оновлення лічильника
            self.session.query(Group).filter_by(group_id=group.group_id).update({"unique_members_count": Group.unique_members_count + 1})

            logger.debug(
                f"Перед комітом: unique_members_count оновлено для групи {group.group_id}, user_id={user_id}"
            )
            self.session.commit()  # Збереження транзакції
            logger.info(f"Користувача {user_id} успішно додано до групи {group.group_id}")
            return True
        except IntegrityError:
            self.session.rollback()
            logger.error(f"Помилка при додаванні користувача {user_id} до групи {group.group_id}", exc_info=True)
            return False

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
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
                group = self.get_group_by_identifier(self.session, group_id)
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

