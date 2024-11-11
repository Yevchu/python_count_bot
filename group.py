from telegram import Update
from telegram.ext import ContextTypes
from services.group_service import GroupService
from admin import is_admin
from db_config import SessionLocal

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with SessionLocal() as session:
        group_service = GroupService(session)

        group_id = update.effective_chat.id
        group_title = update.effective_chat.title

        group = group_service.get_or_creat_group(group_id, group_title)

        for user in update.message.new_chat_members:
            if user.id != context.bot.id:
                group_service.add_unique_member(group, user.id)

async def count_active_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return
    
    active_groups = GroupService.get_active_groups()
    counts = []

    for group in active_groups:
        counts.append(
            f'Група "{group.group_name}": Максимальна кількість унікальних учасників - {group.unique_members_count}'
            )

    if counts:
        await context.bot.send_message(update.effective_user.id, "\n".join(counts))
    else:
        await context.bot.send_message(update.effective_user.id, "Бот ще не доданий до жодної активної групи.")

async def count_specific_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return
    
    if not context.args:
        await update.message.reply_text("Введіть ID або точну назву групи для отримання інформації. Приклад: /specific_group <group_id або 'назва групи'>")
        return

    group_identifier = " ".join(context.args).strip()

    with SessionLocal() as session:
        group = GroupService.get_group_by_identifier(session, group_identifier)

    if group:
        message = (f'Група "{group.group_name}": Максимальна кількість унікальних учасників - '
                   f'{group.unique_members_count}')
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Групу не знайдено або бот не активний у цій групі.")
