import os
import logging

import datetime 

import pytz
from dotenv import load_dotenv
load_dotenv()

from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters, DictPersistence
from telegram import ReplyKeyboardMarkup

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

WELCOME = 0
JOB_SEARCH_FLOW = 1
SUBMIT_PHOTO_FLOW = 2
PARSE_PHOTO_FLOW = 3

JOB_SEARCH_BUTTON = "💼 Find job"
SUBMIT_PHOTO_BUTTON = "📸 Submit photo"
PARSE_PHOTO_BUTTON = "📝 Parse photo"
RESTART_BUTTON = "🔄 Restart"

menu_kb = ReplyKeyboardMarkup([[JOB_SEARCH_BUTTON, SUBMIT_PHOTO_BUTTON, PARSE_PHOTO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)

def start_command(update, context):
    update.message.reply_text(
        'Hi! This bot is created to help people who fled war find job in the Netherlands. What would you like to do? ', 
        reply_markup=menu_kb
        )
    return WELCOME

def job_search_command(update, context):
    update.message.reply_text(
        "Let's help you find a job", 
        reply_markup=menu_kb
        )

def submit_photo_command(update, context):
    update.message.reply_text(
        "Please sumbit your photo", 
        reply_markup=menu_kb
        )

def parse_photo_command(update, context):
    update.message.reply_text(
        "Please parse this photo", 
        reply_markup=menu_kb
        )

def help_command(update, context):
    update.message.reply_text("Use /start to test this bot.")


def free_input_command(update, context):
    update.message.reply_text("Sorry, I didn't undersrtand what you said. Try using one of our commands", reply_markup=menu_kb)


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    dict_persistence = DictPersistence(store_user_data=True)
    updater = Updater(token=os.getenv('API_KEY'), use_context=True, persistence=dict_persistence)

    dp = updater.dispatcher

    handler = ConversationHandler(
      entry_points=[CommandHandler('start', start_command)],
      states={
            WELCOME: [
                MessageHandler(filters=Filters.text(JOB_SEARCH_BUTTON), callback=job_search_command),
                MessageHandler(filters=Filters.text(SUBMIT_PHOTO_BUTTON), callback=submit_photo_command),
                MessageHandler(filters=Filters.text(PARSE_PHOTO_BUTTON), callback=parse_photo_command),
                MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command),
                ],
      },
      fallbacks=[MessageHandler(Filters.text, free_input_command)],
      )

    updater.dispatcher.add_handler(handler)

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()