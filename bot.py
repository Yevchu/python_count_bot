import logging
import json
import os
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, ApplicationBuilder, ConversationHandler
from dotenv import load_dotenv

load_dotenv()
# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

unique_users = set()
max_unique_count = 0
monitored_groups = set()
group_data = {}

# Файл для зберігання ID груп та ID адмінів
GROUPS_FILE = 'groups.json'
ADMINS_FILE = 'admins.json'

# Задайте ID супер адміністратора
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID'))

# Стан для ConversationHandler
ADD_ADMIN = range(1)

# def load_groups():
#     """Завантажити ID груп з JSON-файлу."""
#     global monitored_groups
#     if os.path.exists(GROUPS_FILE):
#         with open(GROUPS_FILE, 'r') as file:
#             monitored_groups = set(json.load(file))

# def save_groups():
#     """Зберегти ID груп у JSON-файл."""
#     with open(GROUPS_FILE, 'w') as file:
#         json.dump(list(monitored_groups), file)

def load_admins():
    """Завантажити ID адмінів з JSON-файлу."""
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'r') as file:
            return set(json.load(file))
    return set()

def save_admins(admins):
    """Зберегти ID адмінів у JSON-файл."""
    with open(ADMINS_FILE, 'w') as file:
        json.dump(list(admins), file)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привіт! Я рахую унікальних учасників чату.')

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global group_data

    # Отримання ID та назви групи
    group_id = str(update.effective_chat.id)
    group_title = update.effective_chat.title

    # Якщо група ще не існує, ініціалізуйте її
    if group_id not in group_data:
        group_data[group_id] = {
            'title': group_title,
            'unique_users': set(),
            'max_unique_count': 0
        }

    # Додаємо нових учасників до унікальних учасників групи
    for user in update.message.new_chat_members:
        group_data[group_id]['unique_users'].add(user.id)

    # Оновлення максимального підрахунку унікальних учасників
    current_count = len(group_data[group_id]['unique_users'])
    if current_count > group_data[group_id]['max_unique_count']:
        group_data[group_id]['max_unique_count'] = current_count

    # # Зберігаємо дані групи
    # save_groups()

async def count_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in [SUPER_ADMIN_ID] + list(load_admins()):
        counts = []
        for group_id, data in group_data.items():
            counts.append(f'Група "{data["title"]}": Максимальна кількість унікальних учасників: {data["max_unique_count"]}')
        
        await context.bot.send_message(update.effective_user.id, "\n".join(counts) if counts else "Бот ще не доданий до жодної групи.")
    else:
        await context.bot.send_message(update.effective_user.id, 'Вибачте, у вас немає доступу до цього бота.')

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPER_ADMIN_ID:
        await update.message.reply_text('У вас нема прав для додавання адміністратора')
        return ConversationHandler.END
    
    await update.message.reply_text('Введіть ID або тег Telegram користувача, якого хочете зробити адміном')
    return ADD_ADMIN

async def add_admin_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    admins = load_admins()
    admin_username = ''

    # Додавання адміністратора 
    try:
        new_admin_id = int(user_input)
    except ValueError:
        new_admin_username = user_input.strip('@')
        admin_username = new_admin_username
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, new_admin_username)
        new_admin_id = chat_member.user.id
    
    admins.add(new_admin_id)
    save_admins(admins)

    await update.message.reply_text(f'Користувач {admin_username} був доданий як адмін')
    return ConversationHandler.END


def main() -> None:
    # load_groups()  # Завантажити моніторингові групи під час запуску
    load_admins()  # Завантажити адмінів під час запуску
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    add_admin_handler = ConversationHandler(
        entry_points=[CommandHandler('add_admin', add_admin_start)],
        states={
            ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_process)]
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    application.add_handler(CommandHandler('count', count_members))
    application.add_handler(add_admin_handler)

    application.run_polling()
if __name__ == '__main__':
    main()
