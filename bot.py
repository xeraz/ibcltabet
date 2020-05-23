from telegram.ext import Updater
import configparser
import os
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram import InlineKeyboardButton, Poll, ParseMode
from telegram.ext import  PollAnswerHandler, PollHandler
from telegram.utils.helpers import mention_html

import logging

class ibCleanerBot:
    def __init__(self, configfile):
        self.config = configparser.ConfigParser()
        self.config.read(configfile)
        # del_msg = {bot_msg_id: {"del_msg_id": del_msg_id, "vote_count": 2}}
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
        context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

    def askdelete(self, update, context):
        del_msg_id = update.message.reply_to_message.message_id
        self.del_msg["delete_msg_id"] = del_msg_id
        del_msg_name = update.message.reply_to_message.chat.first_name
        questions = ['വേണം','വേണ്ട']
        message = context.bot.sendPoll(update.effective_chat.id, "ഈ മെസേജ് കളയട്ടേ?", questions,
                                    is_anonymous=False, type='regular', allows_multiple_answers=False, reply_to_message_id=del_msg_id)
        payload = {message.poll.id: {"questions": questions, "message_id": message.message_id,
                                 "chat_id": update.effective_chat.id, "answers": 0}}
        context.bot_data.update(payload)
        
        # keyboard = [[InlineKeyboardButton("ആയിക്കോട്ടെ", callback_data='1'),
        #     InlineKeyboardButton("വേണ്ട", callback_data='2')]]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        # bot_msg = update.message.reply_text('അപ്പോ എന്നാ {} ന്റെ മെസേജങ്ങ് കളഞ്ഞേക്കട്ടെ?:'.format(del_msg_name), reply_markup=reply_markup)
        #bot_msg_id = bot_msg.message_id
        #self.del_msg[bot_msg_id] = {"del_msg_id": del_msg_id, "vote_count": 0}
        #print("MSG : {0} VOT:{1} BOT:{2}".format(self.del_msg[bot_msg_id]["del_msg_id"], self.del_msg[bot_msg_id]["vote_count"], bot_msg_id))

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
        print ("selected options -1", selected_options)
        answer_string = ""
        for question_id in selected_options:
            if question_id != selected_options[-1]:
                answer_string += questions[question_id] + " and "
            else:
                answer_string += questions[question_id]
        user_mention = mention_html(update.effective_user.id, update.effective_user.full_name)
        context.bot.send_message(context.bot_data[poll_id]["chat_id"],
                                 "{} feels {}!".format(user_mention, answer_string),
                                 parse_mode=ParseMode.HTML)
        if selected_options[0] == 0:
            context.bot_data[poll_id]["answers"] += 1

        # Close poll after three participants voted
        if context.bot_data[poll_id]["answers"] == 3:
            context.bot.stop_poll(context.bot_data[poll_id]["chat_id"],
                                  context.bot_data[poll_id]["message_id"])
    
    
    def delete(self, update, context):
        if update.poll.is_closed:
            print ("test closed")
            return

        #print ("poll options", update.poll.options[0].voter_count)  
        if update.poll.options[0].voter_count == 3:
            try:
                quiz_data = context.bot_data[update.poll.id]
                print ("quiz data is", quiz_data)
                
        # this means this poll answer update is from an old poll, we can't stop it then
            except KeyError:
                print(update.poll.id)
                print("Test Keyerror")
                return
            
            #context.bot.stop_poll(quiz_data["chat_id"], quiz_data["message_id"])
            context.bot.delete_message(chat_id=quiz_data["chat_id"], message_id=self.del_msg["delete_msg_id"])

        # answers = update.poll.options
        # print (answers)
        # ret = ""

        # for answer in answers:
        #     if answer.voter_count == 1:
        #         ret = answer.text
        # print(ret)
        # return ret
        
        # query = update.callback_query
        # bot_msg_id = query.message.message_id
        # self.del_msg[bot_msg_id]["vote_count"] +=1
        # print("MSG : {0} VOT:{1} BOT:{2}".format(self.del_msg[bot_msg_id]["del_msg_id"], self.del_msg[bot_msg_id]["vote_count"], bot_msg_id))
        # if (self.del_msg[bot_msg_id]["vote_count"] < 3):
        #     query.answer()
        #     keyboard = [[InlineKeyboardButton("ആയിക്കോട്ടെ "+f'[{self.del_msg[bot_msg_id]["vote_count"]}]', callback_data='1'),
        #         InlineKeyboardButton("വേണ്ട", callback_data='2')]]
        #     reply_markup = InlineKeyboardMarkup(keyboard)
        #     context.bot.edit_message_text(chat_id=query.message.chat_id,
        #         message_id=query.message.message_id, text='അപ്പോ എന്നാ മെസേജങ്ങ് കളഞ്ഞേക്കട്ടെ?:', reply_markup=reply_markup)
        # else:
        #     context.bot.delete_message(chat_id=query.message.chat_id, message_id=self.del_msg[bot_msg_id]["del_msg_id"])
        #     context.bot.send_message(chat_id=query.message.chat_id, message_id=query.message.message_id, text='ആ മെസേജങ്ങ് കളഞ്ഞു.')

if __name__ == '__main__':
    ibcBot = ibCleanerBot("config.ini")
    ibcBot.initialize_bot()
