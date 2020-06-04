import configparser
import os
import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, run_async
from telegram.ext import  Filters, CallbackQueryHandler, PollAnswerHandler, PollHandler
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, Poll, ParseMode 
from telegram.utils.helpers import mention_html
from translation import Translation


class ibCleanerBot:
    def __init__(self, configfile):
        config = configparser.ConfigParser()
        config.read(configfile)
        self.DEFAULT_VOTE_COUNT = int(config['PARAMS']['DEFAULT_VOTE_COUNT'])
        self.DEFAULT_DELETE_TIMEOUT = int(config['PARAMS']['DEFAULT_DELETE_TIMEOUT'])
        self.TOKEN = config['KEYS']['BOT_API']

    def initialize_bot(self):
        updater = Updater(token=self.TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                             level=logging.INFO)
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)
        askdelete_handler = MessageHandler(Filters.regex('^@' + updater.bot.username + '$'), self.askdelete)
        askdelete_ban_handler = MessageHandler(Filters.regex('^@' + updater.bot.username + ' ban$'), self.askdelete_ban)
        dispatcher.add_handler(askdelete_handler)
        dispatcher.add_handler(askdelete_ban_handler)
        dispatcher.add_handler(PollAnswerHandler(self.receive_poll_answer))
        dispatcher.add_handler(PollHandler(self.delete))
        updater.start_polling()

    @run_async
    def start(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text=Translation.BOT_WELCOME)

    @run_async
    def askdelete(self, update, context):
        self.ask_func(update, context)

    @run_async
    def askdelete_ban(self, update, context):
        self.ask_func(update, context, ban=True)

    def ask_func(self, update, context, ban=False):
        if not update.message.reply_to_message:
            return
        update.message.delete()
        
        del_msg_id = update.message.reply_to_message.message_id
        del_msg_name = update.message.reply_to_message.from_user.first_name
        original_member = context.bot.get_chat_member(update.effective_chat.id,
                                                 update.message.reply_to_message.from_user.id)
        if original_member['status'] in ('creator', 'administrator'):
            return

        question_string = Translation.QUESTION_STRING
        if ban:
            question_string = Translation.QUESTION_STRING_BAN

        questions = [Translation.YES, Translation.NO]
        message = context.bot.sendPoll(update.effective_chat.id,
                                       question_string.format(del_msg_name),
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
        
        if selected_options[0] == 0:
            context.bot_data[poll_id]['count']['yes'] += 1
        elif selected_options[0] == 1:
            context.bot_data[poll_id]['count']['no'] += 1

        # Close poll after three participants voted
        print('foo ', self.DEFAULT_VOTE_COUNT)
        if context.bot_data[poll_id]['count']['yes'] == self.DEFAULT_VOTE_COUNT or \
           context.bot_data[poll_id]['count']['no'] == self.DEFAULT_VOTE_COUNT:
            context.bot.stop_poll(context.bot_data[poll_id]['chat'],
                                  context.bot_data[poll_id]['message_id'])
            context.job_queue.run_once(self.sched_delete, self.DEFAULT_DELETE_TIMEOUT,
                                       context=(context.bot_data[poll_id]['chat'],
                                                context.bot_data[poll_id]['message_id']))

    @run_async
    def delete(self, update, context): 
        if update.poll.options[0].voter_count == self.DEFAULT_VOTE_COUNT:
            context.bot.delete_message(chat_id=context.bot_data[update.poll.id]['chat'],
                                       message_id=context.bot_data[update.poll.id]['msg_to_delete'])
            if context.bot_data[update.poll.id]['ban']:
                context.bot.kick_chat_member(chat_id=context.bot_data[update.poll.id]['chat'],
                                             user_id=context.bot_data[update.poll.id]['sender_id'])
        if update.poll.is_closed:
            print ("test closed")
            return    

       
if __name__ == '__main__':
    ibcBot = ibCleanerBot("config.ini")
    ibcBot.initialize_bot()
