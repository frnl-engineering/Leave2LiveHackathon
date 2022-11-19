import os
import json
import logging

import uuid
import datetime

import pytz
from datetime import datetime as dt

from google_map_class import GoogleMapsClass

from database import DBService 


from dotenv import load_dotenv

load_dotenv()

from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters, DictPersistence, \
    ContextTypes, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

gm = GoogleMapsClass()

amsterdam_timezone = pytz.timezone('Europe/Amsterdam')

with open('responses.json') as f:
    responses = json.load(f)

WELCOME = 0
JOB_SEARCH_FLOW = 1
SUBMIT_JOB_FLOW = 2
PARSE_PHOTO_FLOW = 3
AWAITING_JOB_APPLICANT_NAME = 4
AWAITING_JOB_APPLICANT_POSTCODE = 5
CONFIRM_JOB_APPLICANT_POSTCODE = 6
SAVE_JOB_SEARCH_APPLICATION = 7
SUBMIT_PHOTO_FLOW = 8
SUBMIT_LINK_FLOW = 9
AWAITING_JOB_APPLICANT_LANGUAGE = 10

JOB_SEARCH_BUTTON = "💼 Find job"
SUBMIT_PHOTO_BUTTON = "📸 Submit job"
PARSE_PHOTO_BUTTON = "📝 Parse photo"
RESTART_BUTTON = "🔄 Restart"
YES_BUTTON = "✅ Yes"
NO_BUTTON = "❌ No"
UPLOAD_PHOTO_BUTTON = "📸 Upload photo"
SHARE_LINK_BUTTON = "📝 Share a link/text"
SUBMIT_CATEGORY_BUTTON = "Submit"

JOB_CATEGORIES = {
    "COURIER_BUTTON": "☐ 🚚 Courier",
    "WAITER_BUTTON": "☐ 💁 Waiter / hostess",
    "HANDYMAN_BUTTON": "☐ 🔨Handyman in the kitchen / in the hotel"
    }


keyboard = [
    [InlineKeyboardButton(JOB_CATEGORIES["COURIER_BUTTON"], callback_data='COURIER_BUTTON')], 
    [InlineKeyboardButton(JOB_CATEGORIES["WAITER_BUTTON"], callback_data='WAITER_BUTTON')], 
    [InlineKeyboardButton(JOB_CATEGORIES["HANDYMAN_BUTTON"], callback_data='HANDYMAN_BUTTON')], 
    [InlineKeyboardButton(SUBMIT_CATEGORY_BUTTON, callback_data=SUBMIT_CATEGORY_BUTTON)]]
reply_markup = InlineKeyboardMarkup(keyboard)

menu_kb = ReplyKeyboardMarkup([[JOB_SEARCH_BUTTON, SUBMIT_PHOTO_BUTTON, PARSE_PHOTO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)

dbservice = DBService(db_name=os.getenv("DB_NAME"), connection_string=os.getenv("DB_URI"))

def start_command(update, context):
    logger.info('%s: start_command' % update.message.from_user['id'])
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=responses["WELCOME_MESSAGE"],
        reply_markup=menu_kb)
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    # context.bot.delete_message(
    #     chat_id=update.message.chat_id,
    #     message_id=update.message.message_id
    # )
    return WELCOME

def job_search_ask_name(update, context):
    logger.info('%s: job_search_ask_name' % update.message.from_user['id'])
    _create_user_data_object(update, context)
    dbservice.register_user(update.message)
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=responses["JOB_SEARCH_ASK_NAME"]
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    # context.bot.delete_message(
    #     chat_id=update.message.chat_id,
    #     message_id=update.message.message_id
    # )
    return AWAITING_JOB_APPLICANT_NAME

def job_search_ask_postcode(update, context):
    logger.info('%s: job_search_ask_postcode' % update.message.from_user['id'])
    context.user_data['user_data']['first_name'] = update.effective_message.text
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=responses["JOB_SEARCH_ASK_POSTCODE"]
    )
    context.bot.delete_message(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )
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
        address_summary = address_summary.replace('{city}', context.user_data['user_data']['city'])

    if not postcode_is_correct or not address_summary:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=responses["WRONG_POSTCODE"]
            )
        context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        return AWAITING_JOB_APPLICANT_POSTCODE

    else:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=address_summary,
            reply_markup=ReplyKeyboardMarkup([[YES_BUTTON, NO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)
        )
        context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        return CONFIRM_JOB_APPLICANT_POSTCODE

def job_search_ask_language(update, context):
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=responses["JOB_SEARCH_ASK_LANGUAGE"],
        reply_markup=ReplyKeyboardMarkup([[YES_BUTTON, NO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)
        )
    context.bot.delete_message(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )
    return AWAITING_JOB_APPLICANT_LANGUAGE

def job_search_ask_job_categories(update, context):
    context.user_data['user_data']['speak_english'] = update.effective_message.text
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=responses["JOB_SEARCH_ASK_CATEGORIES"],
        reply_markup=reply_markup
        )
    context.bot.delete_message(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )
    return SAVE_JOB_SEARCH_APPLICATION

def update_button(callback_text):

    if '✔️' in JOB_CATEGORIES[callback_text]:
        JOB_CATEGORIES[callback_text] = JOB_CATEGORIES[callback_text].replace('✔️', '☐')
    elif '☐' in JOB_CATEGORIES[callback_text]:
        JOB_CATEGORIES[callback_text] = JOB_CATEGORIES[callback_text].replace('☐', '✔️')

    return JOB_CATEGORIES

def keyboard_callback(update, context):
    query = update.callback_query

    if query.data == SUBMIT_CATEGORY_BUTTON:
        return job_search_save_application(update, context, query)

    else:
        JOB_CATEGORIES = update_button(query.data)

        query.answer(f'selected: {JOB_CATEGORIES[query.data]}')

        keyboard = []
        for category in JOB_CATEGORIES:
            keyboard.append([InlineKeyboardButton(JOB_CATEGORIES[category], callback_data=category)])
        keyboard.append([InlineKeyboardButton(SUBMIT_CATEGORY_BUTTON, callback_data=SUBMIT_CATEGORY_BUTTON)])
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.edit_message_reply_markup(
            chat_id=update.callback_query.message.chat.id,
            message_id=update.callback_query.message.message_id, 
            reply_markup=reply_markup
        )
        return SAVE_JOB_SEARCH_APPLICATION


def job_search_save_application(update, context, query):
    context.user_data['user_data']['job_category'] = update.effective_message.text
    context.user_data['user_data']['timestamp'] = dt.utcnow().replace(tzinfo=amsterdam_timezone)

    job_applicant_summary = responses["JOB_APPLICANT_SUMMARY"]
    for field in ['first_name', 'city', 'speak_english', 'job_category']:
        job_applicant_summary = job_applicant_summary.replace('{' + field + '}', context.user_data['user_data'][field])
        dbservice.update_user_data(update.message, {field: context.user_data['user_data'][field]})

    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=responses["JOB_SEARCH_SUMMARY"])
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=job_applicant_summary)
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=responses["JOB_SEARCH_END"], 
        reply_markup=menu_kb)
    context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
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
            'speak_english': None,
            "job_category": None
        }
        logger.info('set default user data %s' % context.user_data['user_data'])

    context.user_data['user_data']['username'] = user_data['username']


def submit_job_command(update, context):
    update.message.reply_text(
        responses["SUBMIT_PHOTO_MESSAGE_1"]
        )
    update.message.reply_text(
        responses["SUBMIT_PHOTO_MESSAGE_2"]
        )
    update.message.reply_text(
        responses["SUBMIT_PHOTO_MESSAGE_3"],
        reply_markup=ReplyKeyboardMarkup([[UPLOAD_PHOTO_BUTTON, SHARE_LINK_BUTTON]], one_time_keyboard=True)
    )
    return SUBMIT_JOB_FLOW


def submit_photo(update, context):
    update.message.reply_text(
        responses["SUBMIT_PHOTO"]
    )
    return SUBMIT_PHOTO_FLOW


def submit_link(update, context):
    update.message.reply_text(
        responses["SUBMIT_LINK"]
    )
    return SUBMIT_LINK_FLOW

def image_handler(update, context):
    msg_file = update.message.photo[0].file_id
    obj = context.bot.get_file(msg_file)
    if not os.path.exists("media/"):
        os.makedirs("media/")
    file_uri = f"media/{str(uuid.uuid4())}.jpg"
    obj.download(file_uri)

    update.message.reply_text("Image received", reply_markup=menu_kb)
    return WELCOME

def link_handler(update, context):
    # todo: XXX
    update.message.reply_text("Text received", reply_markup=menu_kb)
    return WELCOME


def notify(context) -> None:
    chat_id = context.job.context['chat_id']
    user_id = context.job.context['user_id']
    # job_industry = "Cafe and restaurants"
    # location = "Enschede, Netherlands"

    user_filter = dbservice.get_user_data(user_id=user_id)
    jobs_details = dbservice.get_jobs_by_user_filter(user_filter=user_filter)

    if not jobs_details:
        context.bot.send_message(chat_id=chat_id, text="Hi, no jobs found today")
        return

    message = "Hi, today we found {0} job(s) for you:\n".format(len(jobs_details))
    for job in jobs_details:
        message += "Job title: {0}\nCity: {1}\nCompany: {2}\nSalary per hour: {3}\nLink: {4}\n\n".format(
            job["title"], job["city"], job["company"], job["salary"], job["link"])

    logger.info("Notification to %s", chat_id)

    context.bot.send_message(chat_id=chat_id, text=message)


def parse_photo_command(update: Update, context) -> None:
    update.message.reply_text(
        "Please parse this photo",
        reply_markup=menu_kb
    )

    chat_id = update.effective_chat.id
    ten_minutes = 5  # 60 * 10 # 10 minutes in seconds
    job_context = {"user_id": update.message.from_user.id, "chat_id": chat_id}
    context.job_queue.run_once(callback=notify, when=ten_minutes, context=job_context)
    # Whatever you pass here as context is available in the job.context variable of the callback


def help_command(update, context):
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Use /start to test this bot.")
    context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )


def free_input_command(update, context):
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Sorry, I didn't undersrtand what you said. Try using one of our commands", reply_markup=menu_kb)
    context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )


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
                MessageHandler(filters=Filters.text(SUBMIT_PHOTO_BUTTON), callback=submit_job_command),
                MessageHandler(filters=Filters.text(PARSE_PHOTO_BUTTON), callback=parse_photo_command),
                MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command),
                ],
            AWAITING_JOB_APPLICANT_NAME: [MessageHandler(filters=None, callback=job_search_ask_postcode)],
            AWAITING_JOB_APPLICANT_POSTCODE: [MessageHandler(filters=None, callback=job_search_confirm_postcode)],
            CONFIRM_JOB_APPLICANT_POSTCODE: [
                MessageHandler(filters=Filters.text(YES_BUTTON), callback=job_search_ask_language),
                MessageHandler(filters=Filters.text(NO_BUTTON), callback=job_search_ask_postcode)
            ],
            AWAITING_JOB_APPLICANT_LANGUAGE: [MessageHandler(filters=None, callback=job_search_ask_job_categories)],
            SAVE_JOB_SEARCH_APPLICATION: [
                CallbackQueryHandler(keyboard_callback)
                ],
            SUBMIT_JOB_FLOW: [
              MessageHandler(filters=Filters.text(UPLOAD_PHOTO_BUTTON), callback=submit_photo),
              MessageHandler(filters=Filters.text(SHARE_LINK_BUTTON), callback=submit_link)
            ],
            SUBMIT_PHOTO_FLOW: [
                MessageHandler(filters=Filters.photo, callback=image_handler)
            ],
            SUBMIT_LINK_FLOW: [
                MessageHandler(filters=None, callback=link_handler)  # todo: update callback
            ]
      },
      fallbacks=[MessageHandler(Filters.text, free_input_command)],
      )

    updater.dispatcher.add_handler(handler)
    updater.dispatcher.add_handler(CommandHandler('start', start_command))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
