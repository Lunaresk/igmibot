from ..bottoken import getConn
from openpyxl import (Workbook, load_workbook)
from datetime import date

months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
heads = ["Vorname", "Nachname", "Email-Adresse", "Kaffee/Tee", "Softgetränke", "Wasser", "Schokolade", "Bier", "Alter Betrag", "Bezahlt", "Neuer Betrag"]

def initDB():
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    conn.rollback()
    cur.execute("CREATE TABLE IF NOT EXISTS Members(EMail TEXT PRIMARY KEY NOT NULL, FirstName TEXT NOT NULL DEFAULT 'John', LastName TEXT NOT NULL DEFAULT 'Doe');")
    cur.execute("CREATE TABLE IF NOT EXISTS TelegramID(Id BIGINT PRIMARY KEY NOT NULL, EMail TEXT REFERENCES Members(EMail), Message INTEGER, Language CHAR(2) NOT NULL DEFAULT 'en');")
    cur.execute("CREATE TABLE IF NOT EXISTS Bill(Email TEXT PRIMARY KEY NOT NULL, Coffee INTEGER NOT NULL DEFAULT 0, Softdrink INTEGER NOT NULL DEFAULT 0, Water INTEGER NOT NULL DEFAULT 0, Choc INTEGER NOT NULL DEFAULT 0, Beer INTEGER NOT NULL DEFAULT 0, Oldbill INTEGER NOT NULL DEFAULT 0, Paid INTEGER NOT NULL DEFAULT 0);")
    conn.commit()

def insertMember(email, lang, tid, message):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("INSERT INTO TelegramID(Id, EMail, Message, Language) VALUES(%s, %s, %s, %s);", (tid, email, message, lang))
    conn.commit()

def isIGMIMember(email):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT EMail FROM Members WHERE Email = %s;", (email,))
    if cur.fetchone():
      return True
    return False

def isTGMember(tid = 0, email = ""):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM TelegramID WHERE Id = %s OR Email = %s;", (tid,email))
    if cur.fetchone():
      return True
    return False

def getMemberPerMail(email):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM Members WHERE EMail = %s;", (email,))
    return cur.fetchone()

def getMemberPerID(tid):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT EMail FROM TelegramID WHERE Id = %s;", (tid,))
    return getMemberPerMail(cur.fetchone()[0])

def getTelegramID(id = 0, mail = ""):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM TelegramID WHERE Id = %s OR Email = %s;", (id, mail))
    return cur.fetchone()

def getTelegramIDList():
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT Id FROM TelegramID;")
    return cur.fetchall()

def getBill(tid):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT * FROM Bill WHERE Email = (SELECT Email FROM TelegramID WHERE Id = %s);", (tid,))
    return cur.fetchone()

def updateMessage(id, message):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("UPDATE TelegramID SET Message = %s WHERE Id = %s;", (message, id))
    conn.commit()

def updateLanguage(id, lang):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("UPDATE TelegramID SET Language = %s WHERE Id = %s;", (lang, id))
    conn.commit()

def updateBill(tid, coffee = 0, soft = 0, water = 0, choc = 0, beer = 0):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("UPDATE Bill SET Coffee = Coffee+%s, Softdrink = Softdrink+%s, Water = Water+%s, Choc = Choc+%s, Beer = Beer+%s WHERE Email = (SELECT Email FROM TelegramID WHERE Id = %s);", (coffee, soft, water, choc, beer, tid))
    conn.commit()

def createExcel(excelDir):
  thisYear = date.today().year
  thisMonth = date.today().month
  if thisMonth == 1:
    thisYear -= 1
    thisMonth = 12
  else:
    thisMonth -= 1
  try:
    wb = load_workbook("{0}/{1}.xlsx".format(excelDir, thisYear))
    ws = wb.create_sheet(months[thisMonth-1])
  except:
    wb = Workbook()
    ws = wb.active
    ws.title = months[thisMonth-1]
  ws.append(heads)
  ws.append([""])
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("SELECT M.firstname, M.lastname, M.Email, B.Coffee, B.Softdrink, B.Water, B.Choc, B.Beer, B.Oldbill/100, B.Paid/100 FROM Members M, Bill B WHERE M.email = B.email ORDER BY M.lastname, M.firstname, M.email ASC;")
    iterator = cur.fetchone()
    while iterator:
      ws.append(list(iterator) + ["=(D{0}*30 + E{0}*100 + F{0}*60 + G{0}*25 + H{0}*100 + I{0}*100 - J{0}*100)/100".format(ws.max_row+1)])
      iterator = cur.fetchone()
  for column in ws.columns:
    if column[0].value in heads[3:8]:
      ws.column_dimensions[column[0].column].width = 13
    else:
      length = max(len(str(cell.value)) for cell in column_cells)
      ws.column_dimensions[column_cells[0].column].width = length
      #ws.column_dimensions[column[0].column].bestFit = True
  wb.save("{0}/{1}.xlsx".format(excelDir, thisYear))
  calculateBill()

def calculateBill():
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("UPDATE Bill SET Oldbill = (Oldbill + Coffee*30 + Softdrink*100 + Water*60 + Choc*25 + Beer*100 - Paid), Coffee = 0, Softdrink = 0, Water = 0, Choc = 0, Beer = 0, Paid = 0;")
    conn.commit()

def removeTelegramID(id = 0, mail = ""):
  with getConn('igmibot') as conn:
    cur = conn.cursor()
    cur.execute("DELETE FROM TelegramID WHERE Id = %s OR EMail = %s;", (id, mail))
    conn.commit()
