import logging
import os
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ApplicationBuilder, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv
from db_config import SessionLocal, PotentialAdmin, Admin, Group, UserGroup, add_super_admin_if_not_exist, init_db
from sqlalchemy.exc import IntegrityError

load_dotenv()
# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID'))
ADD_ADMIN = range(1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = SessionLocal()
    PotentialAdmin.clean_old_potential_admins(session)

    user_id = update.effective_user.id
    username = update.effective_user.username

    existing_admin = session.query(PotentialAdmin).filter_by(user_id=user_id).first()
    if not existing_admin:
        potential_admin = PotentialAdmin(user_id=user_id, username=username)
        session.add(potential_admin)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()

    await update.message.reply_text('Привіт! Я рахую унікальних учасників чату.')
    session.close()

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPER_ADMIN_ID:
        await update.message.reply_text('У вас нема прав для додавання адміністратора')
        return ConversationHandler.END
    await update.message.reply_text('Введіть ID або тег Telegram користувача, якого хочете зробити адміном')
    return ADD_ADMIN

async def add_admin_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    session = SessionLocal()

    try:
        # Спробуємо інтерпретувати введення як ID
        new_admin_id = int(user_input)
        new_admin_username = None  # Якщо вводиться ID, не маємо імені користувача
    except ValueError:
        # Якщо введення не є числом, припускаємо, що це тег користувача
        new_admin_username = user_input.strip('@')
        potential_admin = session.query(PotentialAdmin).filter_by(username=new_admin_username).first()
        
        if potential_admin:
            new_admin_id = potential_admin.user_id
        else:
            await update.message.reply_text(
                f"Помилка: Користувач із тегом @{new_admin_username} не надсилав команду /start або не збережений у базі."
            )
            session.close()
            return ConversationHandler.END

    # Додаємо нового адміністратора з username (якщо є)
    new_admin = Admin(user_id=new_admin_id, username=new_admin_username)
    try:
        session.add(new_admin)
        session.commit()
        await update.message.reply_text(f"Користувача @{new_admin_username or new_admin_id} було додано як адміністратора.")
    except IntegrityError:
        session.rollback()
        await update.message.reply_text(f"Користувач @{new_admin_username or new_admin_id} вже є адміністратором.")
    finally:
        session.close()

    return ConversationHandler.END


async def is_admin(user_id):
    session = SessionLocal()
    admin = session.query(Admin).filter_by(user_id=user_id).first()
    session.close()
    return admin is not None

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = SessionLocal()

    # Отримуємо ID та назву групи
    group_id = update.effective_chat.id
    group_title = update.effective_chat.title

    # Отримуємо або створюємо групу
    group = session.query(Group).filter_by(group_id=group_id).first()
    if not group:
        group = Group(group_id=group_id, group_name=group_title, unique_members_count=0)
        session.add(group)
        session.commit()

    # Перевіряємо кожного нового учасника
    for user in update.message.new_chat_members:
        if user.id != context.bot.id:
            # Перевіряємо, чи вже існує запис для цього користувача в даній групі
            user_group = session.query(UserGroup).filter_by(user_id=user.id, group_id=group.id).first()
            if not user_group:
                # Якщо користувача ще немає, додаємо його в групу
                new_user = UserGroup(user_id=user.id, group_id=group.id)
                session.add(new_user)
                
                # Збільшуємо лічильник унікальних учасників
                group.unique_members_count += 1
                session.commit()
    
    session.close()


async def count_active_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return
    
    session = SessionLocal()
    counts = []

    active_groups = session.query(Group).filter_by(is_active=True).all()
    for group in active_groups:
        counts.append(
            f'Група "{group.group_name}": Максимальна кількість унікальних учасників - {group.unique_members_count}'

        )

    if counts:
        await context.bot.send_message(update.effective_user.id, "\n".join(counts))
    else:
        await context.bot.send_message(update.effective_user.id, "Бот ще не доданий до жодної активної групи.")
    session.close()

async def count_specific_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return
    
    session = SessionLocal()
    
    # Перевіряємо, чи передано параметр для ідентифікації групи
    if not context.args:
        await update.message.reply_text("Введіть ID або точну назву групи для отримання інформації. Приклад: /specific_group <group_id або 'назва групи'>")
        session.close()
        return

    # Об'єднуємо параметри команди в один рядок на випадок, якщо назва групи має пробіли
    group_identifier = " ".join(context.args).strip()

    try:
        # Якщо групу ідентифіковано за ID
        group_id = int(group_identifier)
        group = session.query(Group).filter_by(group_id=group_id, is_active=True).first()
    except ValueError:
        # Якщо ідентифікація за назвою
        group = session.query(Group).filter_by(group_name=group_identifier, is_active=True).first()

    if group:
        message = (f'Група "{group.group_name}": Максимальна кількість унікальних учасників - '
                   f'{group.unique_members_count}')
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Групу не знайдено або бот не активний у цій групі.")
    
    session.close()



def main() -> None:
    init_db()

    super_admin_id = SUPER_ADMIN_ID
    add_super_admin_if_not_exist(super_admin_id)

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("add_admin", add_admin_start)],
        states={
            ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_process)],
        },
        fallbacks=[],
    ))

    application.add_handler(CommandHandler('active_groups', count_active_groups))   
    application.add_handler(CommandHandler("specific_group", count_specific_group))

    application.run_polling()


if __name__ == '__main__':
    main()
