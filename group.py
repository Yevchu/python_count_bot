import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from services.group_service import GroupService
from sqlalchemy.exc import IntegrityError
from admin import is_admin
from db_config import SessionLocal

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
REMOVE_GROUP, SPECIFIC_GROUP = range(2)

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Отримано нових учасників у групі '%s' (%d)", update.effective_chat.title, update.effective_chat.id)

    with SessionLocal() as session:
        try:
            group_service = GroupService(session)

            group_id = update.effective_chat.id
            group_title = update.effective_chat.title

            group = group_service.get_or_create_group(group_id, group_title)
            logger.info("Група оброблена: %s (ID: %d)", group_title, group_id)

            # Обробка нових учасників
            for user in update.message.new_chat_members:
                if user.id != context.bot.id:
                    logger.info("Спроба додати користувача: ID %d, ім'я: %s", user.id, user.full_name)
                    try:
                        success = group_service.add_unique_member(group, user.id)
                        if success:
                            logger.info("Успіх: Користувача ID %d, ім'я %s додано до групи '%s'", user.id, user.full_name, group_title)
                        else:
                            logger.warning("Користувач ID %d вже є у групі '%s'", user.id, group_title)

                        # Додаткова перевірка
                        user_record = group_service.get_user(user_id=user.id, group_id=group.group_id)
                        if not user_record:
                            logger.warning("Користувач ID %d не знайдений у базі після додавання. Повторна спроба.", user.id)
                            success = group_service.add_unique_member(group, user.id)
                            if success:
                                logger.info("Повторна спроба успішна: Користувача ID %d додано до групи '%s'", user.id, group_title)
                            else:
                                logger.error("Повторна спроба додавання користувача ID %d не вдалася.", user.id)

                    except IntegrityError as e:
                        session.rollback()
                        logger.error("IntegrityError: Помилка при додаванні користувача ID %d до групи '%s': %s", user.id, group_title, str(e))
                    except Exception as e:
                        session.rollback()
                        logger.error("Помилка: Користувач ID %d не був доданий до групи '%s': %s", user.id, group_title, str(e))

            # Фінальний коміт після обробки всіх учасників
            session.commit()
        except Exception as e:
            session.rollback()
            logger.exception("Невідома помилка при обробці групи '%s' (ID: %d): %s", group_title, group_id, str(e))

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Отримано нову групу '%s' (%d)", update.effective_chat.title, update.effective_chat.id)

    with SessionLocal() as session:
        try:
            group_service = GroupService(session)

            group_id = update.effective_chat.id
            group_title = update.effective_chat.title

            group_service.get_or_create_group(group_id, group_title)
            logger.info("Група оброблена: %s (ID: %d)", group_title, group_id)
        except Exception as e:
            logger.exception("Невідома помилка при обробці групи '%s' (ID: %d): %s", group_title, group_id, str(e))
        
async def max_member_count(bot) -> None:
    with SessionLocal() as session:
        group_service = GroupService(session)
        groups = group_service.get_active_groups()

        for group in groups:
            logger.debug(f"Отримано групи: {[group.group_name for group in groups]}")
            try:
                member_count = await bot.get_chat_member_count(chat_id=group.group_id)

                if group.max_member_count is None:
                    group.max_member_count = 0

                if group.max_member_count < member_count:
                    group.max_member_count = member_count
                    logger.debug(f"Перед комітом: max_member_count для групи {group.group_name} = {group.max_member_count}")
                    session.add(group)
                    session.commit()
                    logger.debug(f"Після коміту: max_member_count для групи {group.group_name} = {group.max_member_count}")
            except Exception as e:
                session.rollback()
                logger.error(f"Помилка отримання даних для групи {group.group_name}: {e}")

async def count_active_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return
    
    active_groups = GroupService.get_active_groups()
    counts = []

    for group in active_groups:
        counts.append(
            f'Група "{group.group_name}": Максимальна кількість учасників - {group.max_member_count}'
            )

    if counts:
        await context.bot.send_message(update.effective_user.id, "\n".join(counts))
    else:
        await context.bot.send_message(update.effective_user.id, "Бот ще не доданий до жодної активної групи.")

async def count_specific_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return ConversationHandler.END
    await update.message.reply_text("Введіть ID або точну назву групи для отримання інформації.")
    return SPECIFIC_GROUP

async def count_specific_group_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_identifier = update.message.text.strip()

    with SessionLocal() as session:
        group = GroupService.get_group_by_identifier(session, group_identifier)
        if group:
            message = (f'Група "{group.group_name}": Максимальна кількість учасників - '
                    f'{group.max_member_count}')
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Групу не знайдено або бот не активний у цій групі.")

    return ConversationHandler.END

async def remove_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return ConversationHandler.END
    await update.message.reply_text("Введіть ID або назву групи, яку хочете видалити.")
    return REMOVE_GROUP
    
async def remove_group_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    with SessionLocal() as session:
        group_service = GroupService(session)

        try:
            result = group_service.delete_group(user_input)
            await update.message.reply_text(result)
        except IntegrityError:
            session.rollback()
            await update.message.reply_text("Виникла помилка при видаленні групи.")
        except Exception as e:
            await update.message.reply_text(f"Помилка: {e}")

    return ConversationHandler.END
    
async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("У вас немає прав на виконання цієї команди.")
        return ConversationHandler.END
    
    group_identifier = ' '.join(context.args).strip() if context.args else update.effective_chat.id

    with SessionLocal() as session:
        group_service = GroupService(session)

        group = group_service.get_group_by_identifier(session=session, group_identifier=group_identifier)

        if group:
            result = group_service.delete_group(group_identifier)
            await context.bot.leave_chat(group.group_id)
            await update.message.reply_text(result or f"Бот покинув групу '{group.group_name}'.")
        else:
            await update.message.reply_text("Групу не знайдено.")

