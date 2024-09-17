import logging
import os
from datetime import datetime

import django
from django.conf import settings
from environs import Env
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flower_shop.settings")
django.setup()

from tg_bot.models import Bouquet, Order

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Команда /start
def start(update: Update, context: CallbackContext) -> None:
    reply_keyboard = [
        ["День рождения", "Свадьба"],
        ["В школу", "Без повода"],
        ["Другой повод"],
    ]

    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text(
        "К какому событию готовимся? Выберите один из вариантов, либо укажите свой:",
        reply_markup=markup,
    )
    context.user_data["waiting_for_event"] = True


# Выбор события
def event_selection(update: Update, context: CallbackContext) -> None:
    if not context.user_data.get("waiting_for_event"):
        return

    event_type = update.message.text

    if event_type == "Другой повод":
        update.message.reply_text(
            "Пожалуйста, напишите, какой именно повод:",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["awaiting_custom_event"] = True
    else:
        context.user_data["event"] = event_type
        context.user_data["awaiting_custom_event"] = False
        ask_for_budget(update, context)
        context.user_data["waiting_for_event"] = False


# Обработка пользовательского события
def custom_event_handler(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("awaiting_custom_event"):
        custom_event = update.message.text
        context.user_data["event"] = custom_event
        context.user_data["awaiting_custom_event"] = False
        ask_for_budget(update, context)


# Запрос бюджета
def ask_for_budget(update: Update, context: CallbackContext) -> None:
    reply_keyboard = [["~500", "~1000", "~2000"], ["больше", "не важно"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("На какую сумму рассчитываете?", reply_markup=markup)


# Выбор бюджета
def budget_selection(update: Update, context: CallbackContext) -> None:
    price = update.message.text
    event_type = context.user_data.get("event")

    bouquet = Bouquet.objects.filter(event_type=event_type, price_range=price).first()

    if bouquet:
        update.message.reply_photo(
            photo=bouquet.photo,
            caption=(
                f"*Описание:* {bouquet.description}\n"
                f"*Состав:* {bouquet.composition}\n"
                f"*Стоимость:* {bouquet.price}\n\n"
                f"*Хотите что-то еще более уникальное? Подберите другой букет из нашей коллекции или закажите консультацию флориста*"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )

        keyboard = [
            [InlineKeyboardButton("Заказать", callback_data=f"order_{bouquet.id}")],
            [
                InlineKeyboardButton(
                    "Заказать консультацию", callback_data="order_consultation"
                ),
                InlineKeyboardButton(
                    "Посмотреть всю коллекцию", callback_data="view_collection"
                ),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    else:
        update.message.reply_text("Извините, подходящий букет не найден.")


# Обработка нажатий на кнопки
def button_handler(update: Update, context: CallbackContext) -> None:
    logger.info("Я в button_handler")  # Лог для отладки
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("order_"):
        bouquet_id = int(data.split("_")[1])
        context.user_data["bouquet_id"] = bouquet_id
        context.user_data["order_step"] = "name"

        logger.info(f"Букет ID: {bouquet_id}, Ожидается ввод имени")
        query.edit_message_text("Пожалуйста, введите ваше имя:")

    elif data == "order_consultation":
        query.edit_message_text(
            "Консультация флориста будет организована. Спасибо за запрос!"
        )

    elif data == "view_collection":
        query.edit_message_text("Вот вся наша коллекция. Выберите понравившийся букет.")


if __name__ == "__main__":
    env = Env()
    env.read_env()

    tg_bot_token = os.environ["TG_BOT_TOKEN"]
    updater = Updater(token=tg_bot_token)
    dp = updater.dispatcher

    # Регистрируем хэндлеры
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(
        MessageHandler(
            Filters.regex(r"(~500|~1000|~2000|больше|не важно)"), budget_selection
        )
    )
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, event_selection))
    dp.add_handler(
        MessageHandler(Filters.text & ~Filters.command, custom_event_handler)
    )

    updater.start_polling()
    logger.info("Бот запущен и работает.")
    updater.idle()
