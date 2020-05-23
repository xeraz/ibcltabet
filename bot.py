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
        self.config = configparser.ConfigParser()
        self.config.read(configfile)

    def initialize_bot(self):
        updater = Updater(token=self.config['KEYS']['bot_api'], use_context=True)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                             level=logging.INFO)
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)
        askdelete_handler = MessageHandler(Filters.regex('@ibcleanerbot'), self.askdelete)
        dispatcher.add_handler(askdelete_handler)
        #updater.dispatcher.add_handler(CallbackQueryHandler(self.delete, pattern='^'+str(1)+'$'))
        #updater.dispatcher.add_handler(CommandHandler('set', self.delete))
        dispatcher.add_handler(PollAnswerHandler(self.receive_poll_answer))
        dispatcher.add_handler(PollHandler(self.delete))  

        updater.start_polling()

    @run_async
    def start(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text=Translation.BOT_WELCOME)

    @run_async
    def askdelete(self, update, context):
        if not update.message.reply_to_message:
            return
        update.message.delete()
        del_msg_id = update.message.reply_to_message.message_id
        del_msg_name = update.message.reply_to_message.from_user.first_name
        original_member = context.bot.get_chat_member(update.effective_chat.id,
                                                 update.message.reply_to_message.from_user.id)
        if original_member['status'] in ('creator', 'administrator'):
            return

        questions = [Translation.YES, Translation.NO]
        message = context.bot.sendPoll(update.effective_chat.id,
                                       Translation.QUESTION_STRING.format(del_msg_name),
                                       questions,
                                       is_anonymous=False,
                                       type='regular',
                                       allows_multiple_answers=False,
                                       reply_to_message_id=del_msg_id)

        context.bot_data[message.poll.id] = {}
        context.bot_data[message.poll.id]['count'] = 0
        context.bot_data[message.poll.id]['msg_to_delete'] = del_msg_id
        context.bot_data[message.poll.id]['chat'] = update.effective_chat.id
        context.bot_data[message.poll.id]['message_id'] = message.message_id

    @run_async
    def receive_poll_answer(self, update, context):
        """Summarize a users poll vote"""
        answer = update.poll_answer
        print(answer)
        poll_id = answer.poll_id
        selected_options = answer.option_ids
        
        if selected_options[0] == 0:
            context.bot_data[poll_id]['count'] += 1

        # Close poll after three participants voted
        if context.bot_data[poll_id]['count'] == Translation.TOTAL_VOTE_COUNT:
            context.bot.stop_poll(context.bot_data[poll_id]['chat'],
                                  context.bot_data[poll_id]['message_id'])

    @run_async
    def delete(self, update, context): 
        if update.poll.options[0].voter_count == Translation.TOTAL_VOTE_COUNT:
            context.bot.delete_message(chat_id=context.bot_data[update.poll.id]['chat'],
                                       message_id=context.bot_data[update.poll.id]['msg_to_delete'])
            
        if update.poll.is_closed:
            print ("test closed")
            return    

       
if __name__ == '__main__':
    ibcBot = ibCleanerBot("config.ini")
    ibcBot.initialize_bot()
