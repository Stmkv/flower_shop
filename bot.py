import logging
import os

import django
import telegram
from django.conf import settings
from environs import Env
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flower_shop.settings")
django.setup()

from tg_bot.models import Event

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


def event_selection(update: Update, context: CallbackContext) -> None:
    event_type = update.message.text

    if event_type == "Другой повод":
        update.message.reply_text(
            "Пожалуйста, напишите, какой именно повод:",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data["awaiting_custom_event"] = (
            True  # Состояние ожидания кастомного повода
        )
    else:
        context.user_data["event"] = event_type
        context.user_data["awaiting_custom_event"] = (
            False  # Убеждаемся, что состояние сброшено
        )
        ask_for_budget(update, context)


def custom_event_handler(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("awaiting_custom_event"):
        custom_event = update.message.text
        context.user_data["event"] = custom_event
        context.user_data["awaiting_custom_event"] = False  # Сбрасываем состояние
        ask_for_budget(update, context)


def ask_for_budget(update: Update, context: CallbackContext) -> None:
    reply_keyboard = [["~500", "~1000", "~2000"], ["больше", "не важно"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text("На какую сумму рассчитываете?", reply_markup=markup)


def budget_selection(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    price = update.message.text
    event_type = context.user_data.get("event")

    # Сохраняем событие и цену в базу данных
    if price in ["~500", "~1000", "~2000", "больше", "не важно"]:
        Event.objects.create(user_id=user_id, event_type=event_type, price=price)
        update.message.reply_text(
            f"Ваш выбор: {event_type}, бюджет: {price}. Спасибо!",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        update.message.reply_text(
            "Пожалуйста, выберите один из предложенных вариантов."
        )


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
        MessageHandler(Filters.text & Filters.regex(r".+"), custom_event_handler)
    )

    updater.start_polling()
    print("Бот в сети")
    updater.idle()
