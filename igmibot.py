from telegram import (InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, Filters)
from ..errorCallback import error_callback
from . import dbFuncs
from . import helpFuncs

import logging
import json

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

transDir = "/home/shiro/gitProjects/telegramBots/igmibot/translations"
excelDir = "/home/shiro/gitProjects/telegramBots/igmibot/excelTables"
documentsDir = "/home/shiro/gitProjects/telegramBots/igmibot/documents"
igmimail = "noreply@igmitest.de"
langs = ["en", "de"]

SETLANG, TGUNDERUSAGE, EMAIL, MAILUNDERUSAGE, CONFIRMATION = range(5)
MAINSCREEN, BILL, BUY, CONFIRMBUY, SETTINGS, LANGUAGE, INFORMATIONS, REVOKE = range(8)

##### First Step: Registration

def start(bot, update):
  lang = getLang(update.message.from_user)
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = json.load(language)
  if dbFuncs.isTGMember(tid = update.message.from_user['id']):
    bot.send_message(chat_id = update.message.chat_id, text = botText['tgUnderUsage'], reply_markup = createKeyboard(botText['underUsageKeyboard']))
    return TGUNDERUSAGE
  bot.send_message(chat_id = update.message.chat_id, text = botText['welcome'], reply_markup = createKeyboard([[[i]*2 for i in langs[j*3:j*3+3]]for j in range(1+int(len(langs)/3))]))
  return SETLANG

def privacy(bot, update):
  lang = getLang(update.message.from_user)
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = json.load(language)
  bot.send_message(chat_id = update.message.chat_id, text = botText['privacy'])

def tgUnderUsage(bot, update):
  choice = update.callback_query.data
  lang = dbFuncs.getTelegramID(id = update.callback_query.from_user['id'])[3]
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = json.load(language)
  oldID = dbFuncs.getTelegramID(id = update.callback_query.from_user['id'])
  try:
    bot.delete_message(chat_id = oldID[0], message_id = oldID[2])
  except:
    bot.edit_message_text(chat_id = oldID[0], message_id = oldID[2], text = "⬇")
  if choice == 'y':
    dbFuncs.removeTelegramID(id = update.callback_query.from_user['id'])
    bot.send_message(chat_id = update.callback_query.from_user['id'], text = botText['tgIdRemoved'])
  elif choice == 'n':
    dbFuncs.updateMessage(update.callback_query.from_user['id'], bot.send_message(chat_id = update.callback_query.from_user['id'], text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard'])).message_id)
  return ConversationHandler.END

def setLang(bot, update, user_data):
  user_data['lang'] = update.callback_query.data
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = json.load(language)
  bot.send_message(chat_id = update.callback_query.from_user['id'], text = botText['langSet'] + botText['enterEmail'])
  return EMAIL

def setMail(bot, update, user_data):
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = json.load(language)
  email = update.message.text.lower()
  if not dbFuncs.isIGMIMember(email):
    bot.send_message(chat_id = update.message.chat_id, text = botText['notRegistered'])
    return EMAIL
  user_data['mail'] = email
  user_data['code'] = helpFuncs.createCode()
  if dbFuncs.isTGMember(email = email):
    bot.send_message(chat_id = update.message.chat_id, text = botText['mailUnderUsage'], reply_markup = createKeyboard(botText['underUsageKeyboard']))
    return MAILUNDERUSAGE
  return sendMail(bot, user_data, update.message.chat_id)

def sendMail(bot, user_data, chatId):
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = json.load(language)
  mailText = botText['mailText'].format(igmimail, user_data['mail'], user_data['code'])
  user_data['tries'] = 5
  if helpFuncs.sendMail(igmimail, [user_data['mail']], mailText):
    bot.send_message(chat_id = chatId, text = botText['codeSent'])
    logger.info(user_data['code'])
    return CONFIRMATION
  else:
    bot.send_message(chat_id = chatId, text = botText['codeNotSent'])
    return EMAIL

def mailUnderUsage(bot, update, user_data):
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = json.load(language)
  if choice == 'y':
    return sendMail(bot, user_data, update.callback_query.from_user['id'])
  elif choice == 'n':
    bot.send_message(chat_id = update.callback_query.from_user['id'], text = botText['enterEmail'])
    return EMAIL

def confirmation(bot, update, user_data):
  with open("{0}/{1}.json".format(transDir, user_data['lang']), 'r') as language:
    botText = json.load(language)
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
    dbFuncs.insertMember(user_data['mail'], user_data['lang'], update.message.from_user['id'], bot.send_message(chat_id = update.message.chat_id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard'])).message_id)
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
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['bill'].format(sum), reply_markup = createKeyboard(botText['billKeyboard']))
  elif number == SETTINGS:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['settings'], reply_markup = createKeyboard(botText['settingsKeyboard']))
  else:
    return error(bot, update.callback_query.from_user['id'])
  return number

def bill(bot, update, user_data):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  number = int(update.callback_query.data)
  if number == BUY:
    user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer'] = [0]*5
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['buy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer']), reply_markup = createKeyboard([[["➖", "{}_-".format(i[1])], [i[0], str(BUY)], ["➕", "{}_+".format(i[1])]] for i in botText['buyKeyboardPart']] + botText['buyKeyboard']))
  elif number == MAINSCREEN:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard']))
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
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['buy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer']), reply_markup = createKeyboard([[["➖", "{}_-".format(i[1])], [i[0], str(BUY)], ["➕", "{}_+".format(i[1])]] for i in botText['buyKeyboardPart']] + botText['buyKeyboard']))
  else:
    number = int(action[0])
    if number == CONFIRMBUY:
      sum = (user_data['soft']*100 + user_data['beer']*100 + user_data['water']*60 + user_data['coffee']*30 + user_data['choc']*25)/100
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['confirmBuy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer'], sum), reply_markup = createKeyboard(botText['confirmBuyKeyboard']))
    elif number == BILL:
      user_data.clear()
      bill = dbFuncs.getBill(update.callback_query.from_user['id'])
      sum = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100 + bill[6])/100
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['bill'].format(sum), reply_markup = createKeyboard(botText['billKeyboard']))
    elif number == MAINSCREEN:
      user_data.clear()
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard']))
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
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['bill'].format(sum), reply_markup = createKeyboard(botText['billKeyboard']))
  elif number == BUY:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['buy'].format(user_data['coffee'], user_data['soft'], user_data['water'], user_data['choc'], user_data['beer']), reply_markup = createKeyboard([[["➖", "{}_-".format(i[1])], [i[0], str(BUY)], ["➕", "{}_+".format(i[1])]] for i in botText['buyKeyboardPart']] + botText['buyKeyboard']))
  elif number == MAINSCREEN:
    user_data.clear()
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard']))
  else:
    return error(bot, update.callback_query.from_user['id'])
  return number

def settings(bot, update):
  bot.answer_callback_query(update.callback_query.id)
  botText = getBotText(update.callback_query.from_user['id'])
  number = int(update.callback_query.data)
  if number == LANGUAGE:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['languageSettings'], reply_markup = createKeyboard([[[i]*2 for i in langs[j*3:j*3+3]]for j in range(1+int(len(langs)/3))]+botText['langinfoKeyboard']))
  elif number == INFORMATIONS:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['informations'], reply_markup = createKeyboard(botText['informationsKeyboard']+botText['langinfoKeyboard']))
  elif number == MAINSCREEN:
    bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard']))
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
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['settings'], reply_markup = createKeyboard(botText['settingsKeyboard']))
    elif number == MAINSCREEN:
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard']))
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
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['languageSettings'], reply_markup = createKeyboard([[[i]*2 for i in langs[j*3:j*3+3]]for j in range(1+int(len(langs)/3))]+botText['langinfoKeyboard']))
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
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['settings'], reply_markup = createKeyboard(botText['settingsKeyboard']))
    elif number == MAINSCREEN:
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard']))
    else:
      return error(bot, update.callback_query.from_user['id'])
    return number
  else:
    if action == "p" or action == "c":
      return INFORMATIONS
    elif action == "r":
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['confirmRevoke'], reply_markup = createKeyboard(botText['underUsageKeyboard']))
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
      bot.edit_message_text(chat_id = update.callback_query.message.chat_id, message_id = update.callback_query.message.message_id, text = botText['informations'], reply_markup = createKeyboard(botText['informationsKeyboard']+botText['langinfoKeyboard']))
      return INFORMATIONS
    else:
      return error(bot, update.callback_query.message.id)

#TODO Finish Settings Section

##### Helpful things

def cancel(bot, update, user_data):
  if 'lang' in user_data:
    lang = user_data['lang']
  else:
    lang = 'en' #TODO
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = json.load(language)
  user_data.clear()
  bot.send_message(chat_id = update.message.chat_id, text = botText['cancelled'])
  return ConversationHandler.END

def createKeyboard(choices):
  keyboard = []
  for i in choices:
    keyboard.append([])
    for j in i:
      keyboard[-1].append(InlineKeyboardButton(text = j[0], callback_data = j[1]))
  return InlineKeyboardMarkup(keyboard)

def getLang(user):
  lang = ""
  if dbFuncs.isTGMember(tid = user['id']):
    lang = dbFuncs.getTelegramID(id = user['id'])[3]
  else:
    if user['language_code']:
      lang = user['language_code'][0:2]
    else:
      lang = "en"
  if lang not in langs:
    lang = "en"
  return lang

def getBotText(id):
  lang = dbFuncs.getTelegramID(id = id)[3]
  with open("{0}/{1}.json".format(transDir, lang), 'r') as language:
    botText = json.load(language)
  return botText

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

def testReminder(bot, job):
  list = dbFuncs.getTelegramIDList()
  for entry in list:
    botText = getBotText(entry[0])
    bill = dbFuncs.getBill(entry[0])
    sumMonth = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100)/100
    sum = (bill[1]*30 + bill[2]*100 + bill[3]*60 + bill[4]*25 + bill[5]*100 + bill[6])/100
    bot.send_message(chat_id = entry[0], text = botText['summary'].format(bill[1], bill[2], bill[3], bill[4], bill[5], sumMonth, sum))
  job.job_queue.run_once(callback = monthlyReminder, when = helpFuncs.testReminder())

def error(bot, id):
    botText = getBotText(id)
    oldID = dbFuncs.getTelegramID(id)
    try:
      bot.delete_message(chat_id = oldID[0], message_id = oldID[2])
    except:
      bot.edit_message_text(chat_id = oldID[0], message_id = oldID[2], text = "⬇")
    bot.send_message(chat_id = id, text = botText['error'])
    dbFuncs.updateMessage(id, bot.send_message(chat_id = id, text = botText['mainScreen'], reply_markup = createKeyboard(botText['mainScreenKeyboard'])).message_id)
    return MAINSCREEN

##### Main Function

def main(updater):
  dbFuncs.initDB()

  dispatcher = updater.dispatcher

  starter = ConversationHandler(
    entry_points = [CommandHandler('start', start, Filters.private)],
    states = {
      SETLANG: [CallbackQueryHandler(setLang, pass_user_data = True)],
      TGUNDERUSAGE: [CallbackQueryHandler(tgUnderUsage)],
      EMAIL: [MessageHandler(filters = Filters.private&Filters.text, callback = setMail, pass_user_data = True)],
      MAILUNDERUSAGE: [CallbackQueryHandler(mailUnderUsage, pass_user_data = True)],
      CONFIRMATION: [MessageHandler(filters = Filters.private&Filters.text, callback = confirmation, pass_user_data = True)]
    },
    fallbacks = [CommandHandler('cancel', cancel, Filters.private, pass_user_data = True)]
  )

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

  dispatcher.add_handler(starter)
  dispatcher.add_handler(control)

  updater.job_queue.run_once(callback = monthlyReminder, when = helpFuncs.nextReminder())
#  updater.job_queue.run_once(callback = testReminder, when = helpFuncs.testReminder())

  updater.start_polling()

  updater.idle()

  updater.stop()