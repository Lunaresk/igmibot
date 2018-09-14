from uuid import uuid4
from ..bottoken import getMail
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

import datetime
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def createCode():
  return str(uuid4())

def sendMail(sender, receiver, message):
  msg = MIMEMultipart()
  msg['From'] = sender
  msg['To'] = ', '.join(receiver)
  msg['Subject'] = Header(message.split("\n", 1)[0], 'utf-8')
  msg.attach(MIMEText(message.split("\n", 1)[1].encode('utf-8'), 'plain', 'utf-8'))
  with getMail('igmibot') as smtp:
    try:
      smtp.sendmail(sender, receiver, msg.as_string())
      return True
    except Exception as error:
      logger.critical(repr(error))
      return False

def isInt(number):
  try:
    int(number)
    return True
  except ValueError:
    return False

def nextReminder():
  today = datetime.date.today()
  thisYear, thisMonth = [today.year, today.month]
  if thisMonth == 12:
    thisMonth = 0
    thisYear += 1
  return datetime.datetime(thisYear, thisMonth+1, 1, 12, 0, 0)

def testReminder():
  now = datetime.datetime.now()
  year, month, day, hour, minute = [now.year, now.month, now.day, now.hour, now.minute]
  return datetime.datetime(year, month, day, hour, minute+1, 0)
