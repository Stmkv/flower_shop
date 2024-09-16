import logging
import os

import telegram
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def start(update: telegram.Update, context: CallbackContext) -> None:
    telegram_id = update.effective_user.id
    if Client.objects.filter(telegram_id=telegram_id).first():
        update_main_menu(update.message)
    else:
        show_main_menu(update.message)


if __name__ == "__main__":
    env = Env()
    env.read_env()

    tg_chat_id = os.environ["TG_CHAT_ID"]
    tg_bot_token = os.environ["TG_BOT_TOKEN"]
    bot = telegram.Bot(token=tg_bot_token)

    updater = Updater(token=tg_bot_token)
    dispetcher = updater.dispatcher
