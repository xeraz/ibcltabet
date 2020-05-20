from telegram.ext import Updater
import configparser
import os
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram import InlineKeyboardButton
config = configparser.ConfigParser()
config.read('config.ini')
updater = Updater(token=config['KEYS']['bot_api'], use_context=True)
dispatcher = updater.dispatcher
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
qcount = 0
dl_message_id = 0

def main():
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    askdelete_handler = MessageHandler(Filters.regex('@ibcleanerbot'), askdelete)
    dispatcher.add_handler(askdelete_handler)
    updater.dispatcher.add_handler(CallbackQueryHandler(delete, pattern='^'+str(1)+'$'))
    updater.start_polling()


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

def askdelete(update, context):
    dlmessage_id = update.message.reply_to_message.message_id
    dlmessage_name = update.message.reply_to_message.chat.first_name
    print (dlmessage_id, dlmessage_name)
    keyboard = [[InlineKeyboardButton("ആയിക്കോട്ടെ", callback_data='1'),
        InlineKeyboardButton("വേണ്ട", callback_data='2')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('അപ്പോ എന്നാ {} ന്റെ മെസേജങ്ങ് കളഞ്ഞേക്കട്ടെ?:'.format(dlmessage_name), reply_markup=reply_markup)
    dl_message_id += dlmessage_id
    print (type(dl_message_id))
    return dlmessage_id

def delete(update, context):
    query = update.callback_query
    global qcount
    qcount += 1
    if (qcount < 3):
        query.answer()
        keyboard = [[InlineKeyboardButton("ആയിക്കോട്ടെ "+f'[{qcount}]', callback_data='1'),
            InlineKeyboardButton("വേണ്ട", callback_data='2')]]
        reply_markup = InlineKeyboardMarkup(keyboard)    

        context.bot.edit_message_text(chat_id=query.message.chat_id,
            message_id=query.message.message_id, text='അപ്പോ എന്നാ മെസേജങ്ങ് കളഞ്ഞേക്കട്ടെ?:', reply_markup=reply_markup)
    else:
        
        context.bot.delete_message(chat_id=query.message.chat_id,
                   message_id=dl_message_id)
        context.bot.send_message(chat_id=query.message.chat_id,
            message_id=query.message.message_id, text='ആ മെസേജങ്ങ് കളഞ്ഞു.')

if __name__ == '__main__':
    main()  

    #query.edit_message_text(text="Selected option: {}".format(query.data))

