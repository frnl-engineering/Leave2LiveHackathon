import os
import json
import logging

import uuid
import datetime

import pytz
from datetime import datetime as dt

import db_service
from google_map_class import GoogleMapsClass

from dotenv import load_dotenv

load_dotenv()

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters, DictPersistence, \
    ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

gm = GoogleMapsClass()

amsterdam_timezone = pytz.timezone('Europe/Amsterdam')

with open('responses.json') as f:
    responses = json.load(f)

WELCOME = 0
JOB_SEARCH_FLOW = 1
SUBMIT_PHOTO_FLOW = 2
PARSE_PHOTO_FLOW = 3
AWAITING_JOB_APPLICANT_NAME = 4
AWAITING_JOB_APPLICANT_POSTCODE = 5
CONFIRM_JOB_APPLICANT_POSTCODE = 6
SAVE_JOB_SEARCH_APPLICATION = 7

JOB_SEARCH_BUTTON = "💼 Find job"
SUBMIT_PHOTO_BUTTON = "📸 Submit photo"
PARSE_PHOTO_BUTTON = "📝 Parse photo"
RESTART_BUTTON = "🔄 Restart"
YES_BUTTON = "✅ Yes"
NO_BUTTON = "❌ No"

menu_kb = ReplyKeyboardMarkup([[JOB_SEARCH_BUTTON, SUBMIT_PHOTO_BUTTON, PARSE_PHOTO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)

def start_command(update, context):
    logger.info('%s: start_command' % update.message.from_user['id'])
    update.message.reply_text(
        responses["WELCOME_MESSAGE"],
        reply_markup=menu_kb
        )
    return WELCOME

def job_search_ask_name(update, context):
    logger.info('%s: job_search_ask_name' % update.message.from_user['id'])
    _create_user_data_object(update, context)
    update.message.reply_text(responses["JOB_SEARCH_ASK_NAME"])
    return AWAITING_JOB_APPLICANT_NAME

def job_search_ask_postcode(update, context):
    logger.info('%s: job_search_ask_postcode' % update.message.from_user['id'])
    context.user_data['user_data']['first_name'] = update.effective_message.text
    update.message.reply_text(responses["JOB_SEARCH_ASK_POSTCODE"])
    return AWAITING_JOB_APPLICANT_POSTCODE


def job_search_confirm_postcode(update, context):
    logger.info('%s: job_search_confirm_postcode' % update.message.from_user['id'])

    found_addresses, postcode_is_correct = gm.find_address_from_input(update.effective_message.text)
    if found_addresses:
        data_to_add = ['city', 'formatted_postcode', 'coordinates']
        for info in data_to_add:
            context.user_data['user_data'][info] = found_addresses[0][info]
            logger.info(f"{update.message.from_user['id']}: {info} was set to {found_addresses[0][info]}")
        address_summary = responses["ADDRESS_SUMMARY"]
        for field in ['city', 'formatted_postcode']:
            address_summary = address_summary.replace('{' + field + '}', context.user_data['user_data'][field])

    if not postcode_is_correct:
        update.message.reply_text(responses["WRONG_POSTCODE"])
        return AWAITING_JOB_APPLICANT_POSTCODE

    else:
        update.message.reply_text(
            address_summary,
            reply_markup=ReplyKeyboardMarkup([[YES_BUTTON, NO_BUTTON]], one_time_keyboard=True)
        )
        return CONFIRM_JOB_APPLICANT_POSTCODE


def job_search_ask_language(update, context):
    update.message.reply_text(
        responses["JOB_SEARCH_ASK_LANGUAGE"],
        reply_markup=ReplyKeyboardMarkup([[YES_BUTTON, NO_BUTTON]], one_time_keyboard=True)
        )
    return SAVE_JOB_SEARCH_APPLICATION

def job_search_save_application(update, context):
    context.user_data['user_data']['speak_english'] = update.effective_message.text
    context.user_data['user_data']['timestamp'] = dt.utcnow().replace(tzinfo=amsterdam_timezone)

    job_applicant_summary = responses["JOB_APPLICANT_SUMMARY"]
    for field in ['first_name', 'city', 'speak_english']:
        job_applicant_summary = job_applicant_summary.replace('{' + field + '}', context.user_data['user_data'][field])
    update.message.reply_text(responses["JOB_SEARCH_SUMMARY"])
    update.message.reply_text(job_applicant_summary)
    update.message.reply_text(responses["JOB_SEARCH_END"], reply_markup=menu_kb)
    return WELCOME

def _create_user_data_object(update, context):

    user_data = update.effective_user

    if not context.user_data.get('user_data'):
        context.user_data['user_data'] = {
            'id': None,
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'user_id': user_data['id'],
            'username': None,
            'city': None,
            'status': 'new',
            'timestamp': None,
            'speak_english': None
        }
        logger.info('set default user data %s' % context.user_data['user_data'])

    context.user_data['user_data']['username'] = user_data['username']


def submit_photo_command(update, context):
    update.message.reply_text(
        "Please sumbit your photo",
        reply_markup=menu_kb
        )
    return SUBMIT_PHOTO_FLOW


def image_handler(update, context):
    msg_file = update.message.photo[0].file_id
    obj = context.bot.get_file(msg_file)
    if not os.path.exists("media/"):
        os.makedirs("media/")
    file_uri = f"media/{str(uuid.uuid4())}.jpg"
    obj.download(file_uri)

    update.message.reply_text("Image received", reply_markup=menu_kb)
    return WELCOME


def notify(context) -> None:
    chat_id = context.job.context
    # job_industry = "Cafe and restaurants"
    # location = "Enschede, Netherlands"

    user_filter = db_service.dbservice.get_user_data(user_id=chat_id)
    jobs_details = db_service.dbservice.get_jobs_by_user_filter(user_filter=user_filter)

    message = "Hi, today we found {0} job(s) for you:\n".format(len(jobs_details))
    for job in jobs_details:
        message += "Job type: {0}\nLocation: {1}\nDistance: {2}\nCompany: {3}\nSalary: {4}\nLink: {5}\n\n".format(
            job["job_type"], job["location"], job["distance"], job["company"], job["salary"], job["link"])

    logger.info("Notification to %s", chat_id)

    context.bot.send_message(chat_id=chat_id, text=message)


def parse_photo_command(update: Update, context) -> None:
    update.message.reply_text(
        "Please parse this photo",
        reply_markup=menu_kb
        )

    chat_id = update.effective_chat.id
    ten_minutes = 5  # 60 * 10 # 10 minutes in seconds
    context.job_queue.run_once(callback=notify, when=ten_minutes, context=chat_id)
    # Whatever you pass here as context is available in the job.context variable of the callback


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
                MessageHandler(filters=Filters.text(JOB_SEARCH_BUTTON), callback=job_search_ask_name),
                MessageHandler(filters=Filters.text(SUBMIT_PHOTO_BUTTON), callback=submit_photo_command),
                MessageHandler(filters=Filters.text(PARSE_PHOTO_BUTTON), callback=parse_photo_command),
                MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command),
                ],
            AWAITING_JOB_APPLICANT_NAME: [MessageHandler(filters=None, callback=job_search_ask_postcode)],
            AWAITING_JOB_APPLICANT_POSTCODE: [MessageHandler(filters=None, callback=job_search_confirm_postcode)],
            CONFIRM_JOB_APPLICANT_POSTCODE: [
                MessageHandler(filters=Filters.text(YES_BUTTON), callback=job_search_ask_language),
                MessageHandler(filters=Filters.text(NO_BUTTON), callback=job_search_ask_postcode)
            ],
            SAVE_JOB_SEARCH_APPLICATION: [MessageHandler(filters=None, callback=job_search_save_application)],
            SUBMIT_PHOTO_FLOW: [
              MessageHandler(filters=Filters.photo, callback=image_handler)
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
