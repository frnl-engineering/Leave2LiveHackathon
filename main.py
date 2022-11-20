import math
import os
import json
import logging

import uuid
import datetime
import random
import base64
import pytz
from datetime import datetime as dt

import ocr
import translate
from google_map_class import GoogleMapsClass

from database import DBService


from dotenv import load_dotenv

from metrics import emit_metric

load_dotenv()

from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, Filters, DictPersistence, \
    ContextTypes, CallbackContext, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s  - %(lineno)d  - %(levelname)s - %(message)s', level=logging.INFO)
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
AWAITING_JOB_ADDRESS = 11
AWAITING_JOB_PHOTO_TITLE = 12
AWAITING_JOB_PHOTO_CITY = 13
AWAITING_JOB_PHOTO_COMPANY = 14
AWAITING_JOB_PHOTO_CATEGOTY = 15

JOB_SEARCH_BUTTON = "💼 Get a job"
SUBSCRIBE_BUTTON = "🔔 Subscribe"
UNSUBSCRIBE_BUTTON = "🔕 Unsubscribe"
SUBMIT_JOB_BUTTON = "📸 Submit new vacancy"
PARSE_PHOTO_BUTTON = "📝 Help by parsing job descriptions"
RESTART_BUTTON = "🔄 Restart"
YES_BUTTON = "✅ Yes"
NO_BUTTON = "❌ No"
UPLOAD_PHOTO_BUTTON = "📸 Upload photo"
SHARE_LINK_BUTTON = "📝 Share a link/text"
COURIER_BUTTON = "Delivery"
WAITER_BUTTON = "Hostess / Waitress"
HANDYMAN_BUTTON = "General worker (kitchen or hotel)"
NEXT_PAGE_BUTTON = "⏭"
PREV_PAGE_BUTTON = "⏮"
SUBMIT_CATEGORY_BUTTON = "✉️ Submit"

JOB_CATEGORIES = {
    "COURIER_BUTTON": "☐ Delivery",
    "WAITER_BUTTON": "☐ Hostess / Waitress",
    "HANDYMAN_BUTTON": "☐ General worker (kitchen or hotel)"
}

keyboard = [
    [InlineKeyboardButton(JOB_CATEGORIES["COURIER_BUTTON"], callback_data='COURIER_BUTTON')],
    [InlineKeyboardButton(JOB_CATEGORIES["WAITER_BUTTON"], callback_data='WAITER_BUTTON')],
    [InlineKeyboardButton(JOB_CATEGORIES["HANDYMAN_BUTTON"], callback_data='HANDYMAN_BUTTON')],
    [InlineKeyboardButton(SUBMIT_CATEGORY_BUTTON, callback_data=SUBMIT_CATEGORY_BUTTON)]]
job_search_reply_markup = InlineKeyboardMarkup(keyboard)

menu_kb_with_unsubscribe =  ReplyKeyboardMarkup([
    [JOB_SEARCH_BUTTON, UNSUBSCRIBE_BUTTON],
    [SUBMIT_JOB_BUTTON],
    [PARSE_PHOTO_BUTTON],
    [RESTART_BUTTON]
], one_time_keyboard=True)

menu_kb = ReplyKeyboardMarkup([
    [JOB_SEARCH_BUTTON, SUBSCRIBE_BUTTON],
    [SUBMIT_JOB_BUTTON],
    [PARSE_PHOTO_BUTTON],
    [RESTART_BUTTON]
], one_time_keyboard=True)

dbservice = DBService(db_name=os.getenv("DB_NAME"), connection_string=os.getenv("DB_URI"))

def start_command(update, context):
    logger.info('%s: start_command' % update.message.from_user['id'])
    update.message.reply_text(
        responses["WELCOME_MESSAGE"],
        reply_markup=menu_kb
    )
    emit_metric(type="etc", action="start_command")

    # On start/restart remove all notifications subscriptions
    remove_job_if_exists(str(update.effective_message.chat_id), context)

    return WELCOME

def job_search_ask_name(update, context):
    logger.info('%s: job_search_ask_name' % update.message.from_user['id'])
    _create_user_data_object(update, context)
    dbservice.register_user(update.message)
    update.message.reply_text(responses["JOB_SEARCH_ASK_NAME"])
    emit_metric(type="etc", action="job_search_ask_name")
    return AWAITING_JOB_APPLICANT_NAME


def job_search_ask_postcode(update, context):
    logger.info('%s: job_search_ask_postcode' % update.message.from_user['id'])
    context.user_data['user_data']['first_name'] = update.effective_message.text
    update.message.reply_text(responses["JOB_SEARCH_ASK_POSTCODE"])
    emit_metric(type="etc", action="job_search_ask_postcode")
    return AWAITING_JOB_APPLICANT_POSTCODE


def job_search_confirm_postcode(update, context):
    logger.info('%s: job_search_confirm_postcode' % update.message.from_user['id'])
    emit_metric(type="etc", action="job_search_confirm_postcode")

    found_addresses, postcode_is_correct = gm.find_address_from_input(update.effective_message.text)
    if found_addresses:
        data_to_add = ['city', 'formatted_postcode', 'coordinates']
        for info in data_to_add:
            context.user_data['user_data'][info] = found_addresses[0][info]
            logger.info(f"{update.message.from_user['id']}: {info} was set to {found_addresses[0][info]}")
        address_summary = responses["ADDRESS_SUMMARY"]
        address_summary = address_summary.replace('{city}', context.user_data['user_data']['city'])

    if not postcode_is_correct or not address_summary:
        update.message.reply_text(responses["WRONG_POSTCODE"])
        return AWAITING_JOB_APPLICANT_POSTCODE

    else:
        update.message.reply_text(
            address_summary,
            reply_markup=ReplyKeyboardMarkup([[YES_BUTTON, NO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)
        )
        return CONFIRM_JOB_APPLICANT_POSTCODE

def job_search_ask_language(update, context):
    update.message.reply_text(
        responses["JOB_SEARCH_ASK_LANGUAGE"],
        reply_markup=ReplyKeyboardMarkup([[YES_BUTTON, NO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)
        )
    emit_metric(type="etc", action="job_search_ask_language")
    return AWAITING_JOB_APPLICANT_LANGUAGE

def job_search_ask_job_categories(update, context):
    context.user_data['user_data']['speak_english'] = update.effective_message.text
    update.message.reply_text(
        responses["JOB_SEARCH_ASK_CATEGORIES"],
        reply_markup=job_search_reply_markup
    )
    emit_metric(type="etc", action="job_search_ask_job_categories")
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
        context.user_data['user_data']['job_category'] = JOB_CATEGORIES

        query.answer(f'selected: {JOB_CATEGORIES[query.data]}')

        keyboard = []
        for category in JOB_CATEGORIES:
            keyboard.append([InlineKeyboardButton(JOB_CATEGORIES[category], callback_data=category)])
        keyboard.append([InlineKeyboardButton(SUBMIT_CATEGORY_BUTTON, callback_data=SUBMIT_CATEGORY_BUTTON)])
        job_search_reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.edit_message_reply_markup(
            chat_id=update.callback_query.message.chat.id,
            message_id=update.callback_query.message.message_id,
            reply_markup=job_search_reply_markup
        )
        return SAVE_JOB_SEARCH_APPLICATION


def prepare_job_categories_for_saving(categories):
    if not categories:
        return {}
    selected_categories = []
    for cat in categories:
        if '✔️' in categories[cat]:
            category = categories[cat].split('✔️')[-1].strip()
            selected_categories.append(category)
    return selected_categories


def job_search_save_application(update, context, query):
    context.user_data['user_data']['job_category'] = prepare_job_categories_for_saving(
        categories=context.user_data['user_data'].get('job_category')
    )
    context.user_data['user_data']['timestamp'] = dt.utcnow().replace(tzinfo=amsterdam_timezone)

    job_applicant_summary = responses["JOB_APPLICANT_SUMMARY"]
    for field in ['first_name', 'city', 'speak_english', 'job_category']:
        if field == "job_category":
            try:
                selected_jobs_text = ", ".join(context.user_data['user_data'][field])
                job_applicant_summary = job_applicant_summary.replace('{' + field + '}', selected_jobs_text)
            except Exception as e:
                print(e)
                continue
        else:
            job_applicant_summary = job_applicant_summary.replace('{' + field + '}', context.user_data['user_data'][field])
        dbservice.update_user_data(
            user_id=context.user_data["user_data"]["user_id"], update_dict={field: context.user_data['user_data'][field]}
        )

    context.bot.send_message(
            chat_id=update.callback_query.message.chat.id,
            text=responses["JOB_SEARCH_SUMMARY"]
    )
    context.bot.send_message(
        chat_id=update.callback_query.message.chat.id,
        text=job_applicant_summary
    )
    context.bot.send_message(
        chat_id=update.callback_query.message.chat.id,
        text=responses["JOB_SEARCH_END"],
        reply_markup=menu_kb
    )
    emit_metric(type="etc", action="job_search_save_application")
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


def parse_job_photo_title(update, context):
    # TODO: get random job from the database/load photo with category "for_parsing". In the end after submitting translation mark it as "parsed"
    all_raw_jobs = dbservice.get_all_raw_jobs()
    random_job = random.choice(all_raw_jobs)
    context.user_data['current_job_to_parse_id'] = random_job["_id"]
    context.user_data['job_object'] = {}
    update.message.reply_text(
        responses["PARSE_PHOTO_INTRO"]
    )
    if random_job['description']:
        update.message.reply_text(
            random_job['description']
        )
    else:
        update.message.reply_text(
            "Random job description"
        )
        # context.bot.send_photo(
        #     chat_id=update.message.chat_id,
        #     photo=open(random_job["file_uri"], 'rb')
        # )
    update.message.reply_text(
        responses["PARSE_PHOTO_ASK_JOB_TITLE"]
        )
    return AWAITING_JOB_PHOTO_TITLE


def parse_job_photo_city(update, context):
    context.user_data['job_object']['title'] = update.effective_message.text
    update.message.reply_text(
        responses["PARSE_PHOTO_ASK_JOB_CITY"]
        )
    return AWAITING_JOB_PHOTO_CITY


def parse_job_photo_company(update, context):
    context.user_data['job_object']['city'] = update.effective_message.text
    update.message.reply_text(
        responses["PARSE_PHOTO_ASK_JOB_COMPANY"]
        )
    return AWAITING_JOB_PHOTO_COMPANY


def parse_job_photo_category(update, context):
    context.user_data['job_object']['company'] = update.effective_message.text
    update.message.reply_text(
        responses["PARSE_PHOTO_ASK_JOB_CATEGORY"],
        reply_markup=ReplyKeyboardMarkup([[COURIER_BUTTON, WAITER_BUTTON, HANDYMAN_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True)
    )
    return AWAITING_JOB_PHOTO_CATEGOTY


def parse_job_photo_thanks(update, context):
    context.user_data['job_object']['category'] = update.effective_message.text
    dbservice.insert_job(
        {
            "id": str(uuid.uuid4()),
            "title": context.user_data['job_object']['title'],
            "company": context.user_data['job_object']['company'],
            "description": "???",
            "link": "???",
            "category": context.user_data['job_object']['category'],
            "city": context.user_data['job_object']['city'],
            "salary": "???",
            "created_at": dt.utcnow(),
            "updated_at": dt.utcnow(),
            "languages": ["English", "Dutch"],
            "status": "active",
        }
    )

    dbservice.update_raw_job_data(context.user_data['current_job_to_parse_id'], update.message.from_user.id)

    update.message.reply_text(
        responses["PARSE_PHOTO_THANKS"], reply_markup=ReplyKeyboardMarkup([[PARSE_PHOTO_BUTTON], [RESTART_BUTTON]], one_time_keyboard=True))
    return WELCOME


def submit_job_command(update, context):
    update.message.reply_text(
        responses["SUBMIT_PHOTO_MESSAGE_1"]
        )
    update.message.reply_text(
        responses["SUBMIT_PHOTO_MESSAGE_2"]
        )
    update.message.reply_text(
        responses["SUBMIT_PHOTO_MESSAGE_3"]
    )
    update.message.reply_text(
        responses["SUBMIT_PHOTO_MESSAGE_4"],
        reply_markup=ReplyKeyboardMarkup([[UPLOAD_PHOTO_BUTTON, SHARE_LINK_BUTTON]], one_time_keyboard=True)
    )
    emit_metric(type="etc", action="submit_job_command")
    return SUBMIT_JOB_FLOW

def submit_photo(update, context):
    update.message.reply_text(
        responses["SUBMIT_PHOTO"]
    )
    emit_metric(type="etc", action="submit_photo")
    return SUBMIT_PHOTO_FLOW


def submit_job_text_link(update, context):
    update.message.reply_text(
        responses["SUBMIT_LINK"]
    )
    emit_metric(type="etc", action="submit_job_text_link")
    return SUBMIT_LINK_FLOW


def image_to_base64(file_uri):
    try:
        with open(file_uri, "rb") as imageFile:
            return base64.b64encode(imageFile.read())
    except Exception as e:
        logger.error(e)
        return None


def image_handler(update, context):
    emit_metric(type="etc", action="image_handler")
    description = ""
    # TODO make transaction atomic
    try:
        msg_file = update.message.photo[-1].file_id
        file_obj = context.bot.get_file(msg_file)
        if not os.path.exists("media/"):
            os.makedirs("media/")
        file_uri = f"media/{str(uuid.uuid4())}.jpg"
        file_obj.download(file_uri)

        description = "Image caption: {}".format(update.message.caption) if update.message.caption else ""
        text, lang = ocr.read_text_from_image_path(file_uri)
        if text:
            description += "\n\nText from the image:\n{0}".format(text)
            translated_text = translate.translate(text)
            if translated_text:
                description += "\n\nTranslated text from the image:\n{0}".format(translated_text)
        # image_base64 = image_to_base64(file_uri)
        dbservice.save_media_uri(message=update.message, image_uri=file_uri)
        raw_job = {
            "description": description,
            "address": None,
            "file_uri": file_uri,
            "checked": False,
            "created_by": update.message.from_user.id,
            "checked_by": None,
            # "image_base64": image_base64,
        }
        current_job_to_submit_id = dbservice.insert_raw_job(raw_job)
        if current_job_to_submit_id:
            context.user_data['current_job_to_submit_id'] = current_job_to_submit_id.inserted_id
        update.message.reply_text("By the way, where did you spot this job? Please type in name of the city and full address if possible.")
    except Exception as e:
        print(e)
        update.message.reply_text("Something went wrong, please try again later.", reply_markup=menu_kb)
        return WELCOME
    return AWAITING_JOB_ADDRESS


def submit_job_text_handler(update, context):
    raw_job = {
        "description": update.message.text,
        "address": None,
        "file_uri": None,
        "checked": False,
        "created_by": update.message.from_user.id,
        "checked_by": None,
    }
    current_job_to_submit_id = dbservice.insert_raw_job(raw_job)
    context.user_data['current_job_to_submit_id'] = current_job_to_submit_id.inserted_id
    update.message.reply_text("By the way, where did you spot this job? Please type in name of the city and full address if possible.")
    emit_metric(type="etc", action="submit_job_text_handler")
    return AWAITING_JOB_ADDRESS

def submit_job_address(update, context):
    context.user_data['job_address'] = update.effective_message.text
    update.message.reply_text("Thank you! We will review this vacancy and if found relevant share with refugees!", reply_markup=menu_kb)
    emit_metric(type="etc", action="submit_job_address")
    dbservice.update_raw_job_data_address(context.user_data['current_job_to_submit_id'], context.user_data['job_address'])
    return WELCOME


# TODO handle ⏭ properly
def traverse_jobs(update, context):
    pass


def format_job(job={}) -> str:
    datetime_format = "%d.%m.%Y %H:%M"
    res = ""

    row_template = "{0}: {1}\n"
    if job["title"]:
        res += row_template.format(responses["JOB_TITLE"], job["title"])
    if job["city"]:
        res += row_template.format(responses["JOB_CITY"], job["city"])
    if job["company"]:
        res += row_template.format(responses["JOB_COMPANY"], job["company"])
    if job["category"]:
        res += row_template.format(responses["JOB_CATEGORY"], job["category"])
    if job["link"]:
        res += row_template.format(responses["JOB_LINK"], job["link"])
    if job.get("photo"):
        res += row_template.format(responses["JOB_PHOTO"], job["photo"])
    if job["updated_at"]:
        res += row_template.format(responses["JOB_UPDATED_AT"], job["updated_at"].strftime(datetime_format))
    res += "\n"
    return res


def notify_user_about_jobs(context: CallbackContext) -> None:
    chat_id = context.job.context['chat_id']
    user_id = context.job.context['user_id']

    # Trash-like emitting counter metrics

    emit_metric(type="counters", action="unique_users", value=dbservice.count_users())
    emit_metric(type="counters", action="unique_unchecked_jobs", value=dbservice.count_raw_unchecked_jobs())
    emit_metric(type="counters", action="unique_verified_jobs", value=dbservice.count_verified_jobs())

    page = 0
    limit = 5
    user_filter = dbservice.get_user_data(user_id=user_id)
    jobs_details = dbservice.get_jobs_by_user_filter(user_filter=user_filter, page=page, limit=limit)

    total = jobs_details['total']

    if total == 0:  # no jobs for this user
        emit_metric(type="job", action="notification_skipped")
        return
    emit_metric(type="job", action="notification_sent", value=str(total))
    pages = responses["PAGE_TEMPLATE"].format(page + 1, math.ceil(total / limit)) if total > limit else ""
    message = responses["MESSAGE_TEMPLATE"].format(total, pages)
    for job in jobs_details['jobs']:
        message += format_job(job)

    logger.info("Notification to %s", chat_id)

    pagination_buttons = []
    # if page > 0:
    #     pagination_buttons.append(PREV_PAGE_BUTTON)
    # if page < math.ceil(total / limit) - 1:
    #     pagination_buttons.append(NEXT_PAGE_BUTTON)
    context.bot.send_message(
        chat_id=chat_id,
        text=message,
        reply_markup=ReplyKeyboardMarkup([pagination_buttons, [UNSUBSCRIBE_BUTTON, RESTART_BUTTON]], one_time_keyboard=True)
    )


def remove_job_if_exists(name: str, context) -> bool:
    """Remove job with given name. Returns whether job was removed."""

    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False

    for job in current_jobs:
        job.schedule_removal()
    emit_metric(type="user", action="unsubscribe")
    return True


def subscribe_command(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    job_name = str(chat_id)

    # If job already exists, we delete it and stop subscription
    job_removed = remove_job_if_exists(name=job_name, context=context)
    if job_removed:
        update.message.reply_text(responses["UNSUBSCRIBE"], reply_markup=menu_kb)
        return
    emit_metric(type="user", action="subscribe")
    update.message.reply_text(responses["SUBSCRIBE"], reply_markup=menu_kb_with_unsubscribe)

    two_minutes = 30  # each 30 seconds
    job_context = {"user_id": update.message.from_user.id, "chat_id": chat_id}
    context.job_queue.run_repeating(name=job_name, callback=notify_user_about_jobs, interval=two_minutes, context=job_context)
    # Whatever you pass here as context is available in the job.context variable of the callback


def help_command(update, context):
    update.message.reply_text("Use /start to test this bot.")
    emit_metric(type="etc", action="help")
    return WELCOME


def free_input_command(update, context):
    update.message.reply_text("Sorry, I didn't understand what you said. Try using one of our commands", reply_markup=menu_kb)
    emit_metric(type="etc", action="free_input_command")
    return WELCOME


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
                MessageHandler(filters=Filters.text(SUBMIT_JOB_BUTTON), callback=submit_job_command),
                MessageHandler(filters=Filters.text(PARSE_PHOTO_BUTTON), callback=parse_job_photo_title),
                MessageHandler(filters=Filters.text(SUBSCRIBE_BUTTON), callback=subscribe_command),
                MessageHandler(filters=Filters.text(UNSUBSCRIBE_BUTTON), callback=subscribe_command),
                MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command),
                ],
            AWAITING_JOB_APPLICANT_NAME: [MessageHandler(filters=None, callback=job_search_ask_postcode), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
            AWAITING_JOB_APPLICANT_POSTCODE: [MessageHandler(filters=None, callback=job_search_confirm_postcode), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
            CONFIRM_JOB_APPLICANT_POSTCODE: [
                MessageHandler(filters=Filters.text(YES_BUTTON), callback=job_search_ask_language),
                MessageHandler(filters=Filters.text(NO_BUTTON), callback=job_search_ask_postcode),
                CommandHandler('start', start_command),
                MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)
            ],
            AWAITING_JOB_APPLICANT_LANGUAGE: [MessageHandler(filters=None, callback=job_search_ask_job_categories), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
            SAVE_JOB_SEARCH_APPLICATION: [CallbackQueryHandler(keyboard_callback), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
            SUBMIT_JOB_FLOW: [
              MessageHandler(filters=Filters.text(UPLOAD_PHOTO_BUTTON), callback=submit_photo),
              MessageHandler(filters=Filters.text(SHARE_LINK_BUTTON), callback=submit_job_text_link),
              CommandHandler('start', start_command),
              MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)
            ],
            SUBMIT_PHOTO_FLOW: [
                MessageHandler(filters=Filters.photo, callback=image_handler),
                CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), 
                callback=start_command)
            ],
            SUBMIT_LINK_FLOW: [
                MessageHandler(filters=None, callback=submit_job_text_handler),
                CommandHandler('start', start_command), 
                MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)
            ],
            AWAITING_JOB_ADDRESS: [
                MessageHandler(filters=None, callback=submit_job_address), 
                CommandHandler('start', start_command), 
                MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)
            ],
            AWAITING_JOB_PHOTO_TITLE: [MessageHandler(filters=None, callback=parse_job_photo_city), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
            AWAITING_JOB_PHOTO_CITY: [MessageHandler(filters=None, callback=parse_job_photo_company), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
            AWAITING_JOB_PHOTO_COMPANY: [MessageHandler(filters=None, callback=parse_job_photo_category), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
            AWAITING_JOB_PHOTO_CATEGOTY: [MessageHandler(filters=None, callback=parse_job_photo_thanks), CommandHandler('start', start_command), MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command)],
      },
      fallbacks=[MessageHandler(Filters.text, free_input_command)],
      )

    updater.dispatcher.add_handler(handler)
    updater.dispatcher.add_handler(CommandHandler('start', start_command))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.text(JOB_SEARCH_BUTTON), callback=job_search_ask_name))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.text(SUBMIT_JOB_BUTTON), callback=submit_job_command))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.text(PARSE_PHOTO_BUTTON), callback=parse_job_photo_title))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.text(SUBSCRIBE_BUTTON), callback=subscribe_command))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.text(UNSUBSCRIBE_BUTTON), callback=subscribe_command))
    updater.dispatcher.add_handler(MessageHandler(filters=Filters.text(RESTART_BUTTON), callback=start_command))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
