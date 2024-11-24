import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ApplicationBuilder, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv
from db_config import SessionLocal, add_super_admin_if_not_exist, init_db
from admin import (
    SUPER_ADMIN_ID, ADD_ADMIN, ADD_SUPER_ADMIN, REMOVE_ADMIN, 
    add_admin_start, remove_admin_start, add_super_admin_start,
    add_admin_process, remove_admin_process, add_super_admin_process,
    clean_old_potential_admins, add_potential_admin
    )
from group import (
    new_member, max_member_count, new_chat,
    count_active_groups, 
    count_specific_group_start, count_specific_group_process, 
    remove_group_start, remove_group_process,
    leave_group,
    REMOVE_GROUP, SPECIFIC_GROUP,
    )

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME") 


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username

    with SessionLocal() as session:
        clean_old_potential_admins(session)

        add_potential_admin(session, user_id, username)

    await update.message.reply_text('Привіт! Я рахую унікальних учасників чату.')

def scheduler_max_count(bot) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(max_member_count, 'interval', minutes=1, args=[bot])
    scheduler.start()
    logging.info("Планувальник запущено: функція max_member_count буде виконуватись кожні 1 хвилин")


def main() -> None:
    init_db()

    super_admin_id = SUPER_ADMIN_ID
    add_super_admin_if_not_exist(super_admin_id)

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat))

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("add_admin", add_admin_start)],
        states={
            ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_process)],
        },
        fallbacks=[],
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("remove_admin", remove_admin_start)],
        states={
            REMOVE_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_admin_process)],
        },
        fallbacks=[],
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("add_super_admin", add_super_admin_start)],
        states={
            ADD_SUPER_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_super_admin_process)],
        },
        fallbacks=[],
    ))

    application.add_handler(CommandHandler("active_groups", count_active_groups))   
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("specific_group", count_specific_group_start)],
        states={
            SPECIFIC_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, count_specific_group_process)],
        },
        fallbacks=[],
    ))

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("remove_group", remove_group_start)],
        states={
            REMOVE_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_group_process)],
        },
        fallbacks=[],
    ))
    application.add_handler(CommandHandler("leave_group", leave_group))

    scheduler_max_count(application.bot)

    # if not HEROKU_APP_NAME:
    #     raise ValueError("HEROKU_APP_NAME не налаштовано. Додайте цю змінну у вашу конфігурацію.")

    # WEBHOOK_URL = f"https://{HEROKU_APP_NAME}.herokuapp.com/{BOT_TOKEN}"

    # application.run_webhook(
    #     listen="0.0.0.0",  # Слухати на всіх інтерфейсах
    #     port=int(os.getenv("PORT", 8443)),  # Використати змінну PORT для Heroku
    #     url_path=BOT_TOKEN,  # URL шлях вебхука (зазвичай це токен)
    #     webhook_url=WEBHOOK_URL
    # )
    application.run_polling()

if __name__ == '__main__':
    main()
