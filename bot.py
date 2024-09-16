import logging
import os
from datetime import datetime

import django
import telegram
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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flower_shop.settings")
django.setup()

from tg_bot.models import Bouquet, Order

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def start(update: telegram.Update, context: CallbackContext) -> None:
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
        context.user_data["waiting_for_event"] = False  # Сброс флага


def custom_event_handler(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("awaiting_custom_event"):
        custom_event = update.message.text
        context.user_data["event"] = custom_event
        context.user_data["awaiting_custom_event"] = False
        ask_for_budget(update, context)


def ask_for_budget(update: Update, context: CallbackContext) -> None:
    reply_keyboard = [["~500", "~1000", "~2000"], ["больше", "не важно"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("На какую сумму рассчитываете?", reply_markup=markup)


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


def button_handler(update: Update, context: CallbackContext) -> None:
    print("Я в button_handler")
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("order_"):
        bouquet_id = int(data.split("_")[1])
        context.user_data["bouquet_id"] = bouquet_id
        context.user_data["order_step"] = "name"

        query.edit_message_text("Пожалуйста, введите ваше имя:")

    elif data == "order_consultation":
        query.edit_message_text(
            "Консультация флориста будет организована. Спасибо за запрос!"
        )

    elif data == "view_collection":
        query.edit_message_text("Вот вся наша коллекция. Выберите понравившийся букет.")


def order_handler(update: Update, context: CallbackContext) -> None:
    print("Я в order_handler")
    user_id = update.message.from_user.id
    text = update.message.text

    if "order_step" not in context.user_data:
        return

    order_step = context.user_data["order_step"]
    bouquet_id = context.user_data.get("bouquet_id")

    if order_step == "name":
        context.user_data["name"] = text
        update.message.reply_text("Пожалуйста, введите ваш адрес:")
        context.user_data["order_step"] = "address"
    elif order_step == "address":
        context.user_data["address"] = text
        update.message.reply_text(
            "Пожалуйста, введите дату доставки (в формате YYYY-MM-DD):"
        )
        context.user_data["order_step"] = "delivery_date"
    elif order_step == "delivery_date":
        try:
            delivery_date = datetime.strptime(text, "%Y-%m-%d").date()
            context.user_data["delivery_date"] = delivery_date
            update.message.reply_text(
                "Пожалуйста, введите время доставки (в формате HH:MM):"
            )
            context.user_data["order_step"] = "delivery_time"
        except ValueError:
            update.message.reply_text("Неверный формат даты. Попробуйте снова.")
    elif order_step == "delivery_time":
        try:
            delivery_time = datetime.strptime(text, "%H:%M").time()
            context.user_data["delivery_time"] = delivery_time
            bouquet = Bouquet.objects.get(id=context.user_data["bouquet_id"])
            Order.objects.create(
                user_id=user_id,
                bouquet=bouquet,
                name=context.user_data["name"],
                address=context.user_data["address"],
                delivery_date=context.user_data["delivery_date"],
                delivery_time=context.user_data["delivery_time"],
            )
            update.message.reply_text("Ваш заказ был успешно оформлен! Спасибо!")
            context.user_data.clear()  # Сброс всех данных пользователя
        except ValueError:
            update.message.reply_text("Неверный формат времени. Попробуйте снова.")


if __name__ == "__main__":
    env = Env()
    env.read_env()

    tg_chat_id = os.environ["TG_CHAT_ID"]
    tg_bot_token = os.environ["TG_BOT_TOKEN"]
    bot = telegram.Bot(token=tg_bot_token)

    updater = Updater(token=tg_bot_token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(
        MessageHandler(
            Filters.regex(r"(~500|~1000|~2000|больше|не важно)"), budget_selection
        )
    )
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, event_selection))

    dp.add_handler(
        MessageHandler(Filters.text & ~Filters.command, custom_event_handler)
    )

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, order_handler))

    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    print("Бот в сети")
    updater.idle()
