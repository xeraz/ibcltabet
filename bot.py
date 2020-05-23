from telegram.ext import Updater
import configparser
import os
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram import InlineKeyboardButton, Poll, ParseMode
from telegram.ext import  PollAnswerHandler, PollHandler
from telegram.utils.helpers import mention_html
from translation import Translation

import logging

class ibCleanerBot:
    def __init__(self, configfile):
        self.config = configparser.ConfigParser()
        self.config.read(configfile)
        # del_msg = {delete_msg_id:del_msg_id}
        self.del_msg = {}

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

    def start(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text=Translation.BOT_WELCOME)

    def askdelete(self, update, context):
        del_msg_id = update.message.reply_to_message.message_id
        del_msg_username = update.message.message_id
        self.del_msg["delete_msg_id"] = del_msg_id
        self.del_msg["delete_msg_username"] = del_msg_username
        del_msg_name = update.message.reply_to_message.from_user.first_name
        print (del_msg_name)
        questions = [Translation.YES, Translation.NO]
        message = context.bot.sendPoll(update.effective_chat.id, Translation.QUESTION_STRING.format(del_msg_name), questions,
                                    is_anonymous=False, type='regular', allows_multiple_answers=False, reply_to_message_id=del_msg_id)
        payload = {message.poll.id: {"questions": questions, "message_id": message.message_id,
                                 "chat_id": update.effective_chat.id, "answers": 0}}
        context.bot_data.update(payload)
              
    def receive_poll_answer(self, update, context):
        """Summarize a users poll vote"""
        answer = update.poll_answer
        print(answer)
        poll_id = answer.poll_id
        try:
            questions = context.bot_data[poll_id]["questions"]
    # this means this poll answer update is from an old poll, we can't do our answering then
        except KeyError:
            return
        selected_options = answer.option_ids
        
        if selected_options[0] == 0:
            context.bot_data[poll_id]["answers"] += 1

        # Close poll after three participants voted
        if context.bot_data[poll_id]["answers"] == Translation.TOTAL_VOTE_COUNT:       
            context.bot.stop_poll(context.bot_data[poll_id]["chat_id"],
                                   context.bot_data[poll_id]["message_id"])
            
    
    def delete(self, update, context):
        
        #print ("poll options", update.poll.options[0].voter_count)  
        if update.poll.options[0].voter_count == Translation.TOTAL_VOTE_COUNT:
            try:
                quiz_data = context.bot_data[update.poll.id]
                print ("quiz data is", quiz_data)
                
        # this means this poll answer update is from an old poll, we can't stop it then
            except KeyError:
                print(update.poll.id)
                print("Test Keyerror")
                return
            
            #context.bot.stop_poll(quiz_data["chat_id"], quiz_data["message_id"])
            print("chat id is", quiz_data["chat_id"])
            print ("message id is ", self.del_msg["delete_msg_id"])
            context.bot.delete_message(chat_id=quiz_data["chat_id"], message_id=self.del_msg["delete_msg_id"])
            context.bot.delete_message(chat_id=quiz_data["chat_id"], message_id=self.del_msg["delete_msg_username"])
            

        if update.poll.is_closed:
            print ("test closed")
            return    

       
if __name__ == '__main__':
    ibcBot = ibCleanerBot("config.ini")
    ibcBot.initialize_bot()
