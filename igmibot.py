from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from telegram.ext import (CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, Filters)
from ..errorCallback import error_callback
from . import dbFuncs
from . import helpFuncs

import logging
from json import load as jsonload
from pickle import (load as pickleload, dump as pickledump)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Directory for translations, excel documents, IGMI documents; IGMI Mail adress; supported languages
transDir = "/home/shiro/gitProjects/telegramBots/igmibot/translations"
excelDir = "/home/shiro/gitProjects/telegramBots/igmibot/excelTables"
documentsDir = "/home/shiro/gitProjects/telegramBots/igmibot/documents"
backupsDir = "/home/shiro/gitProjects/telegramBots/igmibot/backups"
igmimail = "noreply@wpgcommunity.net"
langs = ["en", "de"]

# These are for the ConversationHandler states
SETLANG, TGUNDERUSAGE, EMAIL, MAILUNDERUSAGE, CONFIRMATION = range(5)
MAINSCREEN, BILL, BUY, CONFIRMBUY, SETTINGS, LANGUAGE, INFORMATIONS, REVOKE = range(8)

##### First Step: Registration

def start(bot, update):
  # Try to get user's language. Otherwise, use english
  lang = getLang(update.message.from_user)
  # Get the right translation and store it in variable botText
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = jsonload(language)
  # Check if telegram-user is already registered and send message if yes
  if dbFuncs.isTGMember(tid = update.message.from_user['id']):
    bot.send_message(chat_id = update.message.chat_id, text = botText['tgUnderUsage'], reply_markup = createReplyKeyboard(botText['underUsageKeyboard']))
    return TGUNDERUSAGE
  # Send welcome message
  bot.send_message(chat_id = update.message.chat_id, text = botText['welcome'], reply_markup = createReplyKeyboard([langs]))
  return SETLANG

#TODO Privacy text. Not yet implemented.
def privacy(bot, update):
  lang = getLang(update.message.from_user)
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = jsonload(language)
  bot.send_message(chat_id = update.message.chat_id, text = botText['privacy'])

# Checks the user's choice, if he wants to cut the connection or not
def tgUnderUsage(bot, update):
  # Save user input and get the language from database (seems not right. will rework it later)
  choice = update.message.text
  lang = dbFuncs.getTelegramID(id = update.message.from_user['id'])[3]
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = jsonload(language)
  # Get the Telegram ID datas from table to get the old message ID
  oldID = dbFuncs.getTelegramID(id = update.message.from_user['id'])
  # Try to delete the old message. If not possible, edit the old message's text to down-arrow.
  try:
    bot.delete_message(chat_id = oldID[0], message_id = oldID[2])
  except:
    bot.edit_message_text(chat_id = oldID[0], message_id = oldID[2], text = "⬇")
  # If user pressed "Yes", break connection and send "restart" message
  if choice == botText['underUsageKeyboard'][0][0][0]:
    dbFuncs.removeTelegramID(id = update.message.from_user['id'])
    bot.send_message(chat_id = update.message.from_user['id'], text = botText['tgIdRemoved'], reply_markup = ReplyKeyboardRemove())
  # If user pressed "No", send Step 2 Main screen again
  elif choice == botText['underUsageKeyboard'][0][1][0]:
    dbFuncs.updateMessage(update.message.from_user['id'], bot.send_message(chat_id = update.message.from_user['id'], text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard'])).message_id)
  # If user typed anything else in chat, tell him what he should use
  else:
    bot.send_message(chat_id = update.message.chat_id, text = botText['useKeyboard'], reply_markup = createReplyKeyboard(botText['underUssageKeyboard']))
    return TGUNDERUSAGE # To stay in this state
  return ConversationHandler.END

# When receiving the language message, this method is triggered
def setLang(bot, update, user_data):
  # Check if input is valid and set language
  if update.message.text in langs:
    user_data['lang'] = update.message.text
  else:
    with open("{0}/{1}.json".format(transDir, getLang(update.message.from_user)), 'r') as language:
      botText = jsonload(language)
    bot.send_message(chat_id = update.message.chat_id, text = botText['useKeyboard'], reply_markup = createReplyKeyboard(botText['underUssageKeyboard']))
    return SETLANG
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = jsonload(language)
  # Send message to enter email
  bot.send_message(chat_id = update.message.chat_id, text = botText['langSet'] + botText['enterEmail'], reply_markup = ReplyKeyboardRemove())
  return EMAIL

# When receiving a message (hopefully an email address), this method is triggered
def setMail(bot, update, user_data):
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = jsonload(language)
  # Save whatever is sent as lowercase
  email = update.message.text.lower()
  # When the mail is not registered, tell the user
  if not dbFuncs.isIGMIMember(email):
    bot.send_message(chat_id = update.message.chat_id, text = botText['notRegistered'])
    return EMAIL
  # Otherwise store mail temporarily and generate a unique code
  user_data['mail'] = email
  user_data['code'] = helpFuncs.createCode()
  # When the mail is already registered from a telegram user, ask for confirmation
  if dbFuncs.isTGMember(email = email):
    bot.send_message(chat_id = update.message.chat_id, text = botText['mailUnderUsage'], reply_markup = createReplyKeyboard(botText['underUsageKeyboard']))
    return MAILUNDERUSAGE
  # Otherwise, send the confirmation mail and tell the user if it worked or not
  return sendMail(bot, user_data, update.message.chat_id)

# Awaiting the confirmation for an used mail adress
def mailUnderUsage(bot, update, user_data):
  choice = update.message.text
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = jsonload(language)
  if choice == botText['underUsageKeyboard'][0][0][0]:
    return sendMail(bot, user_data, update.message.from_user['id'])
  elif choice == botText['underUsageKeyboard'][0][1][0]:
    bot.send_message(chat_id = update.message.from_user['id'], text = botText['enterEmail'])
    return EMAIL
  else:
    bot.send_message(chat_id = update.message.chat_id, text = botText['useKeyboard'], reply_markup = createReplyKeyboard(botText['underUssageKeyboard']))
    return MAILUNDERUSAGE

# Wait for the correct code as input.
def confirmation(bot, update, user_data):
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = jsonload(language)
  if update.message.text == user_data['code']:
    oldID = dbFuncs.getTelegramID(mail = user_data['mail'])
    if not helpFuncs.sendMail(igmimail, [user_data['mail']], botText['confirmedMail'].format(igmimail, user_data['mail'])):
      if oldID and oldID[0] != update.message.chat_id:
        bot.send_message(chat_id = oldID[0], text = botText['foreignLogin'])
        try:
          bot.delete_message(chat_id = oldID[0], message_id = oldID[2])
        except:
          bot.edit_message_text(chat_id = oldID[0], message_id = oldID[2], text = "⬇")
    bot.send_message(chat_id = update.message.chat_id, text = botText['confirmed'])
    if oldID:
      try:
        bot.delete_message(chat_id = oldID[0], message_id = oldID[2])
      except:
        bot.edit_message_text(chat_id = oldID[0], message_id = oldID[2], text = "⬇")
    dbFuncs.insertMember(user_data['mail'], user_data['lang'], update.message.from_user['id'], bot.send_message(chat_id = update.message.chat_id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard'])).message_id)
    return ConversationHandler.END
  else:
    user_data['tries']-=1
    if user_data['tries'] > 0:
      bot.send_message(chat_id = update.message.chat_id, text = botText['wrongCode'].format(user_data['tries']))
      return CONFIRMATION
    else:
      bot.send_message(update.message.chat_id, text = botText['wrongCodeExit']) #TODO set a better message
      user_data.clear()
      return ConversationHandler.END

##### Second Step: Functionality

def mainScreen(bot, update):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  if helpFuncs.isInt(update.callback_query.data):
    number = int(update.callback_query.data)
  else:
    return error(bot, update.callback_query.from_user['id'])
  if number == BILL:
    bill = dbFuncs.getBill(update.callback_query.from_user['id'])
    sum = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100 + bill[6])/100
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['bill'].format(sum), reply_markup = createInlineKeyboard(botText['billKeyboard']))
  elif number == SETTINGS:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['settings'], reply_markup = createInlineKeyboard(botText['settingsKeyboard']))
  else:
    return error(bot, update.callback_query.from_user['id'])
  return number

def bill(bot, update, user_data):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  number = int(update.callback_query.data)
  if number == BUY:
    user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer'] = [0]*5
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['buy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer']), reply_markup = createInlineKeyboard([[["➖", "{}_-".format(i[1])], [i[0], str(BUY)], ["➕", "{}_+".format(i[1])]] for i in botText['buyKeyboardPart']] + botText['buyKeyboard']))
  elif number == MAINSCREEN:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard']))
  else:
    return error(bot, update.callback_query.from_user['id'])
  return number

def buy(bot, update, user_data):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  action = update.callback_query.data.split('_')
  if len(action) > 1:
    if action[1] == '+':
      user_data[action[0]]+=1
    elif action[1] == '-':
      if user_data[action[0]] > 0:
        user_data[action[0]]-=1
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['buy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer']), reply_markup = createInlineKeyboard([[["➖", "{}_-".format(i[1])], [i[0], str(BUY)], ["➕", "{}_+".format(i[1])]] for i in botText['buyKeyboardPart']] + botText['buyKeyboard']))
  else:
    number = int(action[0])
    if number == CONFIRMBUY:
      sum = (user_data['soft']*100 + user_data['beer']*100 + user_data['water']*60 + user_data['coffee']*30 + user_data['choc']*25)/100
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['confirmBuy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer'], sum), reply_markup = createInlineKeyboard(botText['confirmBuyKeyboard']))
    elif number == BILL:
      user_data.clear()
      bill = dbFuncs.getBill(update.callback_query.from_user['id'])
      sum = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100 + bill[6])/100
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['bill'].format(sum), reply_markup = createInlineKeyboard(botText['billKeyboard']))
    elif number == MAINSCREEN:
      user_data.clear()
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard']))
    elif number == BUY:
      return BUY
    else:
      return error(bot, update.callback_query.from_user['id'])
    return number

def confirmBuy(bot, update, user_data):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  number = int(update.callback_query.data)
  if number == BILL:
    dbFuncs.updateBill(update.callback_query.from_user['id'], user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer'])
    user_data.clear()
    bill = dbFuncs.getBill(update.callback_query.from_user['id'])
    sum = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100 + bill[6])/100
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['bill'].format(sum), reply_markup = createInlineKeyboard(botText['billKeyboard']))
  elif number == BUY:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['buy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer']), reply_markup = createInlineKeyboard([[["➖", "{}_-".format(i[1])], [i[0], str(BUY)], ["➕", "{}_+".format(i[1])]] for i in botText['buyKeyboardPart']] + botText['buyKeyboard']))
  elif number == MAINSCREEN:
    user_data.clear()
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard']))
  else:
    return error(bot, update.callback_query.from_user['id'])
  return number

def settings(bot, update):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  number = int(update.callback_query.data)
  if number == LANGUAGE:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['languageSettings'], reply_markup = createInlineKeyboard([[[i]*2 for i in langs[j*3:j*3+3]]for j in range(1+int(len(langs)/3))]+botText['langinfoKeyboard']))
  elif number == INFORMATIONS:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['informations'], reply_markup = createInlineKeyboard(botText['informationsKeyboard']+botText['langinfoKeyboard']))
  elif number == MAINSCREEN:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard']))
  else:
    return error(bot, update.callback_query.from_user['id'])
  return number

def language(bot, update):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  action = update.callback_query.data
  if helpFuncs.isInt(action):
    number = int(action)
    if number == SETTINGS:
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['settings'], reply_markup = createInlineKeyboard(botText['settingsKeyboard']))
    elif number == MAINSCREEN:
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard']))
    else:
      return error(bot, update.callback_query.from_user['id'])
    return number
  else:
    if action not in langs:
      return error(bot, update.callback_query.from_user['id'])
    dbFuncs.updateLanguage(update.callback_query.from_user['id'], action)
    botText2 = getBotText(update.callback_query.from_user['id'])
    if botText != botText2:
      botText = botText2
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['languageSettings'], reply_markup = createInlineKeyboard([[[i]*2 for i in langs[j*3:j*3+3]]for j in range(1+int(len(langs)/3))]+botText['langinfoKeyboard']))
    else:
      bot.answer_callback_query(update.callback_query.id)
    return LANGUAGE

def informations(bot, update):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  action = update.callback_query.data
  if helpFuncs.isInt(action):
    number = int(action)
    if number == SETTINGS:
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['settings'], reply_markup = createInlineKeyboard(botText['settingsKeyboard']))
    elif number == MAINSCREEN:
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard']))
    else:
      return error(bot, update.callback_query.from_user['id'])
    return number
  else:
    if action == "p" or action == "c":
      return INFORMATIONS
    elif action == "r":
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['confirmRevoke'], reply_markup = createInlineKeyboard(botText['underUsageKeyboard']))
      return REVOKE
    else:
      return error(bot, update.callback_query.from_user['id'])

def revoke(bot, update):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  action = update.callback_query.data
  if helpFuncs.isInt(action):
    return error(bot, update.callback_query.from_user['id'])
  else:
    if action == 'y':
      oldID = dbFuncs.getTelegramID(update.callback_query.from_user['id'])
      try:
        bot.delete_message(chat_id = oldID[0], message_id = oldID[2])
      except:
        bot.edit_message_text(chat_id = oldID[0], message_id = oldID[2], text = "⬇")
      dbFuncs.removeTelegramID(id = update.callback_query.from_user['id'])
      bot.send_message(chat_id = update.callback_query.message.chat_id, text = botText['tgIdRemoved'])
      return ConversationHandler.END
    elif action == 'n':
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['informations'], reply_markup = createInlineKeyboard(botText['informationsKeyboard']+botText['langinfoKeyboard']))
      return INFORMATIONS
    else:
      return error(bot, update.callback_query.message.id)

#TODO Finish Settings Section

##### Helpful things

# Cancels current action and removes temporarily saved datas
def cancel(bot, update, user_data):
  if 'lang' in user_data:
    lang = user_data['lang']
  else:
    lang = getLang(update.message.from_user)
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = jsonload(language)
  user_data.clear()
  bot.send_message(chat_id = update.message.chat_id, text = botText['cancelled'])
  return ConversationHandler.END

# Handles mail sending and response
def sendMail(bot, user_data, chatId):
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = jsonload(language)
  # Get mail text and insert some values inside
  mailText = botText['mailText'].format(igmimail, user_data['mail'], user_data['code'])
  # User gets 5 tries to insert the right code (maybe too generous, rework later)
  user_data['tries'] = 5
  # Try to send the mail. If it worked, tell the user. If not, tell the user too
  if helpFuncs.sendMail(igmimail, [user_data['mail']], mailText):
    bot.send_message(chat_id = chatId, text = botText['codeSent'])
    logger.info(user_data['code'])
    return CONFIRMATION
  else:
    bot.send_message(chat_id = chatId, text = botText['codeNotSent'])
    return EMAIL

# Function for creating Inline Keyboards
def createInlineKeyboard(choices):
  keyboard = []
  for i in choices:
    keyboard.append([])
    for j in i:
      keyboard[-1].append(InlineKeyboardButton(text = j[0], callback_data = j[1]))
  return InlineKeyboardMarkup(keyboard)

# Function for creating Reply Keyboards (there might be a way to fuse both for improved performance)
def createReplyKeyboard(choices):
  keyboard = []
  for i in choices:
    keyboard.append([])
    for j in i:
      if '[' in str(j):
        keyboard[-1].append(KeyboardButton(text = j[0]))
      else:
        keyboard[-1].append(KeyboardButton(text = j))
  return ReplyKeyboardMarkup(keyboard, one_time_keyboard = True)

# Function to get the language of a user with limited informations
def getLang(user):
  lang = ""
  if dbFuncs.isTGMember(tid = user['id']):
    return dbFuncs.getTelegramID(id = user['id'])[3]
  else:
    if user['language_code']:
      lang = user['language_code'][0:2]
  if lang not in langs:
    lang = "en"
  return lang

# Function to get the translation dict for an user
def getBotText(id):
  lang = dbFuncs.getTelegramID(id = id)[3]
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = jsonload(language)
  return botText

# Monthly reminder job
def monthlyReminder(bot, job):
  list = dbFuncs.getTelegramIDList()
  for entry in list:
    botText = getBotText(entry[0])
    bill = dbFuncs.getBill(entry[0])
    sumMonth = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100)/100
    sum = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100 + bill[6])/100
    bot.send_message(chat_id = entry[0], text = botText['summary'].format(bill[1], bill[2], bill[3], bill[4], bill[5], sumMonth, sum))
  dbFuncs.createExcel(excelDir)
  job.job_queue.run_once(callback = monthlyReminder, when = helpFuncs.nextReminder())

# Testreminder
#def testReminder(bot, job):
#  list = dbFuncs.getTelegramIDList()
#  for entry in list:
#    botText = getBotText(entry[0])
#    bill = dbFuncs.getBill(entry[0])
#    sumMonth = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100)/100
#    sum = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100 + bill[6])/100
#    bot.send_message(chat_id = entry[0], text = botText['summary'].format(bill[1], bill[2], bill[3], bill[4], bill[5], sumMonth, sum))
#  job.job_queue.run_once(callback = monthlyReminder, when = helpFuncs.testReminder())

# General error handler
def error(bot, id):
    botText = getBotText(id)
    oldID = dbFuncs.getTelegramID(id)
    try:
      bot.delete_message(chat_id = oldID[0], message_id = oldID[2])
    except:
      bot.edit_message_text(chat_id = oldID[0], message_id = oldID[2], text = "⬇")
    bot.send_message(chat_id = id, text = botText['error'])
    dbFuncs.updateMessage(id, bot.send_message(chat_id = id, text = botText['mainScreen'], reply_markup = createInlineKeyboard(botText['mainScreenKeyboard'])).message_id)
    return MAINSCREEN

# Fuction for me to insert alpha tester
def insert(bot, update, args):
  if update.message.from_user['id'] != 114951690:
    bot.send_message(chat_id = update.message.chat_id, text = "You are not allowed to do this.")
  else:
    if len(args) != 3:
      bot.send_message(chat_id = update.message.chat_id, text = "Use it like this:\n/insert <email> <first name> <last name>")
    else:
      dbFuncs.insertNewMember(args[0], args[1], args[2])
      bot.send_message(chat_id = update.message.chat_id, text = "New member inserted.")

##### Main Function

def main(updater):
  # Initialize database if necessary
  dbFuncs.initDB()

  dispatcher = updater.dispatcher
  job_queue = updater.job_queue

  # Step 1 Conversationhandler: Registration
  register = ConversationHandler(
    entry_points = [CommandHandler('start', start, Filters.private)],
    states = {
      SETLANG: [MessageHandler(filters = Filters.private&Filters.text, callback = setLang, pass_user_data = True)],
      TGUNDERUSAGE: [MessageHandler(filters = Filters.private&Filters.text, callback = tgUnderUsage)],
      EMAIL: [MessageHandler(filters = Filters.private&Filters.text, callback = setMail, pass_user_data = True)],
      MAILUNDERUSAGE: [MessageHandler(filters = Filters.private&Filters.text, callback = mailUnderUsage, pass_user_data = True)],
      CONFIRMATION: [MessageHandler(filters = Filters.private&Filters.text, callback = confirmation, pass_user_data = True)]
    },
    fallbacks = [CommandHandler('cancel', cancel, Filters.private, pass_user_data = True)]
  )

  # Step 2 ConversationHandler: Mainscreen
  control = ConversationHandler(
    entry_points = [CallbackQueryHandler(mainScreen)],
    states = {
      MAINSCREEN: [CallbackQueryHandler(mainScreen)],
      BILL: [CallbackQueryHandler(bill, pass_user_data = True)],
      BUY: [CallbackQueryHandler(buy, pass_user_data = True)],
      CONFIRMBUY: [CallbackQueryHandler(confirmBuy, pass_user_data = True)],
      SETTINGS: [CallbackQueryHandler(settings)],
      LANGUAGE: [CallbackQueryHandler(language)],
      INFORMATIONS: [CallbackQueryHandler(informations)],
      REVOKE: [CallbackQueryHandler(revoke)],
    },
    fallbacks = [CommandHandler('cancel', cancel, Filters.private, pass_user_data = True)],
    per_message = True
  )


  dispatcher.add_handler(CommandHandler('insert', insert, Filters.private, pass_args = True))

  # Registering both handlers
  dispatcher.add_handler(register)
  dispatcher.add_handler(control)


  # Registering monthly reminder
  job_queue.run_once(callback = monthlyReminder, when = helpFuncs.nextReminder())

  # Testreminder, reminds every minute.
#  job_queue.run_once(callback = testReminder, when = helpFuncs.testReminder())

  try:
    with open('{0}/userdata'.format(backupsDir), 'rb') as file:
      dispatcher.user_data = pickleload(file)
  except Exception as e:
    logger.warning(repr(e))
  try:
    with open('{0}/register'.format(backupsDir), 'rb') as file:
      register.conversations = pickleload(file)
  except Exception as e:
    logger.warning(repr(e))
  try:
    with open('{0}/control'.format(backupsDir), 'rb') as file:
      control.conversations = pickleload(file)
  except Exception as e:
    logger.warning(repr(e))

  updater.start_polling()

  updater.idle()

  try:
    with open('{0}/userdata'.format(backupsDir), 'wb+') as file:
      pickledump(dispatcher.user_data, file)
  except Exception as e:
    logger.warning(repr(e))
  try:
    with open('{0}/register'.format(backupsDir), 'wb+') as file:
      pickledump(register.conversations, file)
  except Exception as e:
    logger.warning(repr(e))
  try:
    with open('{0}/control'.format(backupsDir), 'wb+') as file:
      pickledump(control.conversations, file)
  except Exception as e:
    logger.warning(repr(e))
