import os
import logging
import i18n
import json

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    run_async,
    Filters,
    CallbackQueryHandler,
    PollAnswerHandler,
    PollHandler)
from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Poll,
    ParseMode)
from telegram.utils.helpers import mention_html
from translation import Translation
from database import mod_or_make_chat, get_chat


i18n.load_path.append('locale')
i18n.set('filename_format', '{locale}.{format}')
i18n.set('skip_locale_root_data', True)
i18n.set('fallback', 'en')


def localize(func):
    def inner(*args, **kwargs):
        locale = ''
        chat_data = get_chat(args[1].effective_chat.id)
        if chat_data:
            locale = chat_data.locale or ''
        i18n.set('locale', locale)
        func(*args, **kwargs)
    return inner


class ibCleanerBot:
    def __init__(self, config):
        self.DEFAULT_VOTE_COUNT = int(config.DEFAULT_VOTE_COUNT)
        self.DEFAULT_DELETE_TIMEOUT = int(config.DEFAULT_DELETE_TIMEOUT)
        self.TOKEN = config.bot_api

    def initialize_bot(self, is_env):
        updater = Updater(token=self.TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        self.foo = dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                             level=logging.INFO)
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)
        askdelete_handler = MessageHandler(
            Filters.regex('^@' + updater.bot.username + '$'), self.askdelete)
        askdelete_ban_handler = MessageHandler(
            Filters.regex('^@' + updater.bot.username + ' ban$'), self.askdelete_ban)
        set_handler = CommandHandler('set', self.set_cmd)
        dispatcher.add_handler(askdelete_handler)
        dispatcher.add_handler(askdelete_ban_handler)
        dispatcher.add_handler(PollAnswerHandler(self.receive_poll_answer))
        dispatcher.add_handler(PollHandler(self.delete))
        dispatcher.add_handler(set_handler)

        if is_env:
            updater.start_webhook(
                listen="0.0.0.0",
                # (c) https://t.me/c/1186975633/22915
                port=self.config.port,
                url_path=self.config.bot_api
            )
            updater.bot.set_webhook(url=self.config.url + self.config.bot_api)
        else:
            updater.start_polling()


    @run_async
    def set_cmd(self, update, context):
        if len(context.args) < 2:
            return
        if context.args[0] == 'locale':
            res = mod_or_make_chat(update.effective_chat.id, locale=context.args[1])
            update.message.reply_text(res)
        elif context.args[0] == 'votes':
            res = mod_or_make_chat(update.effective_chat.id, vote_count=context.args[1])
            update.message.reply_text(res)
        elif context.args[0] == 'timeout':
            res = mod_or_make_chat(update.effective_chat.id, delete_timeout=context.args[1])
            update.message.reply_text(res)

    @run_async
    @localize
    def start(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=i18n.t('bot_welcome',
                                             name=context.bot.first_name,
                                             username=context.bot.username))

    @run_async
    def askdelete(self, update, context): 
        self.ask_func(update, context)

    @run_async
    def askdelete_ban(self, update, context):
        self.ask_func(update, context, ban=True)

    @localize
    def ask_func(self, update, context, ban=False):
        if not update.message.reply_to_message:
            return
        update.message.delete()

        del_msg_id = update.message.reply_to_message.message_id
        del_msg_name = update.message.reply_to_message.from_user.first_name
        original_member = context.bot.get_chat_member(
            update.effective_chat.id,
            update.message.reply_to_message.from_user.id)
        if original_member['status'] in ('creator', 'administrator'):
            return

        question_string = i18n.t('question_string', name=del_msg_name)
        if ban:
            question_string = i18n.t('question_string_ban', name=del_msg_name)

        questions = [i18n.t('yes'), i18n.t('no')]

        message = context.bot.sendPoll(update.effective_chat.id,
                                       question_string,
                                       questions,
                                       is_anonymous=False,
                                       type='regular',
                                       allows_multiple_answers=False,
                                       reply_to_message_id=del_msg_id)

        context.bot_data[message.poll.id] = {}
        context.bot_data[message.poll.id]['count'] = {
            'yes': 0,
            'no': 0
        }
        context.bot_data[message.poll.id]['msg_to_delete'] = del_msg_id
        context.bot_data[message.poll.id]['chat'] = update.effective_chat.id
        context.bot_data[message.poll.id]['message_id'] = message.message_id
        context.bot_data[message.poll.id]['sender_id'] = original_member.user.id
        context.bot_data[message.poll.id]['ban'] = ban

    def sched_delete(self, context):
        job_ctx = context.job.context
        context.bot.delete_message(job_ctx[0], job_ctx[1])

    @run_async
    def receive_poll_answer(self, update, context):
        """Summarize a users poll vote"""
        answer = update.poll_answer
        poll_id = answer.poll_id
        selected_options = answer.option_ids
        
        timeout = self.DEFAULT_DELETE_TIMEOUT
        vote_count = self.DEFAULT_VOTE_COUNT
        chat_data = get_chat(context.bot_data[poll_id]['chat'])
        if chat_data:
            timeout = chat_data.delete_timeout or self.DEFAULT_DELETE_TIMEOUT
            vote_count = chat_data.vote_count or self.DEFAULT_VOTE_COUNT

        if selected_options[0] == 0:
            context.bot_data[poll_id]['count']['yes'] += 1
        elif selected_options[0] == 1:
            context.bot_data[poll_id]['count']['no'] += 1

        # Close poll after three participants voted
        if context.bot_data[poll_id]['count']['yes'] == vote_count or \
           context.bot_data[poll_id]['count']['no'] == vote_count:
            context.bot.stop_poll(context.bot_data[poll_id]['chat'],
                                  context.bot_data[poll_id]['message_id'])
            context.job_queue.run_once(self.sched_delete, timeout,
                                       context=(context.bot_data[poll_id]['chat'],
                                                context.bot_data[poll_id]['message_id']))

    @run_async
    def delete(self, update, context):
        vote_count = self.DEFAULT_VOTE_COUNT
        chat_data = get_chat(context.bot_data[update.poll.id]['chat'])
        if chat_data:
            vote_count = chat_data.vote_count or self.DEFAULT_VOTE_COUNT

        if update.poll.options[0].voter_count == vote_count:
            context.bot.delete_message(chat_id=context.bot_data[update.poll.id]['chat'],
                                       message_id=context.bot_data[update.poll.id]['msg_to_delete'])
            if context.bot_data[update.poll.id]['ban']:
                context.bot.kick_chat_member(chat_id=context.bot_data[update.poll.id]['chat'],
                                             user_id=context.bot_data[update.poll.id]['sender_id'])
        if update.poll.is_closed:
            print ("test closed")
            return


if __name__ == '__main__':
    # code to allow switching between
    # ENV vars, and config.py
    # incase of hosting in ephimeral filesystems

    IS_ENV = bool(os.environ.get("IS_ENV", False))
    if IS_ENV:
        from sampleconfig import Config
    else:
        from config import Config

    ibcBot = ibCleanerBot(Config)
    ibcBot.initialize_bot(IS_ENV)
