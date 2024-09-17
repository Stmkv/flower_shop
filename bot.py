import logging
import os
from datetime import datetime

import django
import requests
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
    print("Я в start")
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
    context.user_data.clear()  # Очищаем состояние пользователя
    context.user_data["waiting_for_event"] = True


# Выбор события
def event_selection(update: Update, context: CallbackContext) -> None:
    print("Я в event_selection")
    if context.user_data.get("awaiting_full_name"):
        return handle_message(update, context)
    if context.user_data.get("awaiting_phone"):
        return handle_message(update, context)
    if context.user_data.get("awaiting_address"):
        return handle_message(update, context)
    if context.user_data.get("awaiting_time"):
        return handle_message(update, context)

    event_type = update.message.text

    if event_type == "Другой повод":
        update.message.reply_text(
            "Пожалуйста, напишите, какой именно повод:",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["awaiting_custom_event"] = True
    else:
        context.user_data["event"] = event_type
        ask_for_budget(update, context)
        context.user_data["waiting_for_event"] = False


# Обработка пользовательского события
def custom_event_handler(update: Update, context: CallbackContext) -> None:
    print("Я в custom_event_handler")
    if context.user_data.get("awaiting_custom_event"):
        custom_event = update.message.text
        context.user_data["event"] = custom_event
        ask_for_budget(update, context)
        context.user_data["awaiting_custom_event"] = False


# Запрос бюджета
def ask_for_budget(update: Update, context: CallbackContext) -> None:
    print("Я в ask_for_budget")
    reply_keyboard = [["~500", "~1000", "~2000"], ["больше", "не важно"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("На какую сумму рассчитываете?", reply_markup=markup)
    context.user_data["waiting_for_budget"] = True


# Выбор бюджета
def budget_selection(update: Update, context: CallbackContext) -> None:
    print("Я в budget_selection")
    if not context.user_data.get("waiting_for_budget"):
        return

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

    context.user_data["waiting_for_budget"] = False


# Обработка нажатий на кнопки
def button_handler(update: Update, context: CallbackContext) -> None:
    print("Я в button_handler")
    logger.info("Я в button_handler")  # Лог для отладки
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("order_"):
        new_order(update, context)

    elif data == "order_consultation":
        query.edit_message_text(
            "Консультация флориста будет организована. Спасибо за запрос!"
        )

    elif data == "view_collection":
        query.edit_message_text("Вот вся наша коллекция. Выберите понравившийся букет.")


def new_order(update: Update, context: CallbackContext) -> None:
    print("Я в new_order")
    query = update.callback_query
    query.answer()
    query.message.reply_text(
        "Пожалуйста, введите ваше имя:",
    )
    context.user_data["awaiting_full_name"] = True


def handle_message(update: Update, context: CallbackContext) -> None:
    message_text = update.message.text

    if context.user_data.get("awaiting_full_name"):
        context.user_data["full_name"] = message_text
        update.message.reply_text("Введите ваш номер телефона:")
        context.user_data["awaiting_phone"] = True
        context.user_data["awaiting_full_name"] = False
        return

    if context.user_data.get("awaiting_phone"):
        context.user_data["phone"] = message_text
        update.message.reply_text("Введите адрес доставки:")
        context.user_data["awaiting_address"] = True
        context.user_data["awaiting_phone"] = False
        return

    if context.user_data.get("awaiting_address"):
        context.user_data["address"] = message_text
        update.message.reply_text("Напишите время доставки:")
        context.user_data["awaiting_time"] = True
        context.user_data["awaiting_address"] = False
        return

    if context.user_data.get("awaiting_time"):
        context.user_data["time"] = message_text

        telegram_id = update.message.from_user.id
        name = context.user_data["full_name"]
        phone = context.user_data["phone"]
        address = context.user_data["address"]
        time = context.user_data["time"]
        bouquet = Bouquet.objects.get(id=1)

        process_flower(
            update, context, telegram_id, name, phone, address, time, bouquet
        )
        update.message.reply_text("Заказ принят! Спасибо за ваш выбор.")
        context.user_data.clear()  # Очищаем данные после завершения заказа


def process_flower(update, context, telegram_id, name, phone, address, time, bouquet):
    order = Order(
        user_id=telegram_id,
        bouquet=bouquet,
        name=name,
        address=address,
        delivery_time=time,
    )
    order.save()

    order_details = f"""Получен новый заказ
    № - {order.id}
    Клиент: {name}
    Номер телефона: {phone}
    Букет: {bouquet}
    Цена: {bouquet.price}
    Адрес доставки: {address}
    Дата создания заказа: {order.date_ordered}
    Время доставки: {order.delivery_time}
    """
    send_order_confirmation(tg_chat_id, order_details, tg_bot_token)
    context.user_data.clear()


def send_order_confirmation(
    tg_chat_id: int, order_details: str, tg_bot_token: str
) -> None:
    url = f"https://api.telegram.org/bot{tg_bot_token}/sendMessage"
    payload = {"chat_id": tg_chat_id, "text": order_details, "parse_mode": "HTML"}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Сообщение успешно отправлено.")
    else:
        print(f"Ошибка отправки сообщения: {response.text}")


if __name__ == "__main__":
    env = Env()
    env.read_env()
    tg_chat_id = os.environ["TG_CHAT_ID"]
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
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    logger.info("Бот запущен и работает.")
    updater.idle()
