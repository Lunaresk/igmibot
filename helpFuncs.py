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

# Function for sending a mail
def sendMail(sender, receiver, message):
  #MIME for easy formatting email content
  msg = MIMEMultipart()
  # From, To, Subject defines the header
  msg['From'] = sender
  msg['To'] = ', '.join(receiver)
  msg['Subject'] = Header(message.split("\n", 1)[0], 'utf-8')
  # Attach meesage content. 'message' has to be split at the first \n occurence
  # to separate header from content
  msg.attach(MIMEText(message.split("\n", 1)[1].encode('utf-8'), 'plain', 'utf-8'))
  with getMail('igmibot') as smtp:
    try: # try to send the mail
      smtp.sendmail(sender, receiver, msg.as_string())
      return True
    except Exception as error:
      logger.critical(repr(error))
      return False

# Function to evaluate if an object can be cast to int
def isInt(number):
  try:
    int(number)
    return True
  except ValueError:
    return False

# Function to get the next month. Returns datetime object
def nextReminder():
  today = datetime.date.today()
  thisYear, thisMonth = [today.year, today.month]
  if thisMonth == 12:
    thisMonth = 0
    thisYear += 1
  return datetime.datetime(thisYear, thisMonth+1, 1, 12, 0, 0)


# Just a test function, now deprecated
# Maybe I need it again for testing purposes
def testReminder():
  now = datetime.datetime.now()
  year, month, day, hour, minute = [now.year, now.month, now.day, now.hour, now.minute]
  return datetime.datetime(year, month, day, hour, minute+1, 0)
