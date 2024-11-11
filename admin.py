import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from db_config import PotentialAdmin, SessionLocal
from sqlalchemy.orm import Session
from services.admin_service import AdminService

load_dotenv()

SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID'))
ADD_ADMIN, ADD_SUPER_ADMIN, REMOVE_ADMIN = range(3)

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_super_admin(update.effective_user.id):
        await update.message.reply_text('У вас нема прав для додавання адміністратора')
        return ConversationHandler.END
    await update.message.reply_text('Введіть ID або тег Telegram користувача, якого хочете зробити адміном')
    return ADD_ADMIN

async def add_admin_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    with SessionLocal() as session:
        admin_service = AdminService(session)

        try:
            new_admin_id = int(user_input)
            new_admin_username = None  
        except ValueError:
            new_admin_username = user_input.strip('@')
            potential_admin = admin_service.get_potential_admin_by_username(new_admin_username)
            
            if potential_admin:
                new_admin_id = potential_admin.user_id
            else:
                await update.message.reply_text(
                    f"Помилка: Користувач із тегом @{new_admin_username} не надсилав команду /start або не збережений у базі."
                )
                return ConversationHandler.END

        if admin_service.add_admin(new_admin_id, new_admin_username):
            await update.message.reply_text(f"Користувача @{new_admin_username or new_admin_id} було додано як адміністратора.")
        else:
            await update.message.reply_text(f"Користувач @{new_admin_username or new_admin_id} вже є адміністратором.")
    return ConversationHandler.END

async def add_super_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_super_admin(update.effective_user.id):
        await update.message.reply_text('У вас нема прав для додавання суперадміністратора')
        return ConversationHandler.END
    await update.message.reply_text('Введіть ID або тег Telegram користувача, якого хочете зробити адміном')
    return ADD_SUPER_ADMIN

async def add_super_admin_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    with SessionLocal() as session:
        admin_service = AdminService(session)
        try:
            user_id = int(user_input)
            username = None
        except ValueError:
            username = user_input.strip('@')
            potential_admin = admin_service.get_potential_admin_by_username(username)

            if not potential_admin:
                await update.message.reply_text(
                    f"Помилка: Користувач із тегом @{username} не надсилав команду /start або не збережений у базі."
                )
                return
            user_id = potential_admin.user_id
        existing_admin = admin_service.get_admin_by_id(user_id)
        if existing_admin:
            message = admin_service.add_super_admin(existing_admin)
        else:
            message = admin_service.new_super_admin(user_id, username)

        await update.message.reply_text(message)   

async def remove_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_super_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на видалення адміністратора.")
        return ConversationHandler.END
    await update.message.reply_text("Введіть ID або тег Telegram користувача, якого хочете видалити з адмінів.")
    return REMOVE_ADMIN

async def remove_admin_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    with SessionLocal() as session:
        admin_service = AdminService(session)

        try:
            admin_id = int(user_input)
        except ValueError:
            admin_username = user_input.strip('@')
            admin = admin_service.get_admin_by_username(admin_username)

            if not admin:
                await update.message.reply_text(f"Користувача з тегом @{admin_username} не знайдено серед адміністраторів.")
                return ConversationHandler.END
            admin_id = admin.id
        
        result = admin_service.remove_admin_by_id(admin_id)
        await update.message.reply_text(result)
        return ConversationHandler.END

async def is_admin(user_id: int):
    with SessionLocal() as session:
        admin_service = AdminService(session)
        admin = admin_service.get_admin_by_id(user_id)
    return admin is not None

async def is_super_admin(user_id: int):
    with SessionLocal() as session:
        admin_service = AdminService(session)
        super_admin = admin_service.get_super_admin_by_id(user_id)
    return super_admin is not None

def clean_old_potential_admins(session: Session) -> None:
    PotentialAdmin.clean_old_potential_admins(session=session)

def add_potential_admin(session: Session, user_id: int, username: str) -> None:
    potential_admin = PotentialAdmin(user_id=user_id, username=username)
    session.add(potential_admin)
    session.commit()

