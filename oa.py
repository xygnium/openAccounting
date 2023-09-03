#!/usr/bin/env python3

import os
import sys
import mariadb 
import csv
import json
from itertools import islice

cmds = ["help", "q", "cc-old", "accounts", "ac", "zero", "addac"]

cmdDict = {
        "h": "show all cmds",
        "q": "quit pgm",
        "cc": "make transactions csv file from csv file downloaded from BofA credit card account",
        "ck": "make transactions csv file from csv file downloaded from BofA checking account",
        "inx": "chg db - import transactions csv file",
        "ccold": "chg db - add credit card transactions from modified csv file downloaded from Google Sheets",
        "shbal": "show balance",
        "shac": "show account info",
        "addac": "chg db - add account",
        "addx": "chg db - create and add transaction",
        "shx": "show all transactions",
        "ct": "db commit",
        "rb": "db rollback"
        }

drAcct=[]
crAcct=[]
dbEntries=[]

def help():
    for c in cmdDict:
        print("%10s, %s" % (c, cmdDict[c]))

def exitPgm(msg, code):
    print(msg)
    sys.exit(code)

def exitAbnormal(msg):
    dbConn.close()
    exitPgm(msg, -1)

def exitNormal(conn, msg):
    conn.close()
    exitPgm(msg, 0)

def quitWithMsg(msg):
    print(msg)
    return -1

def quit(conn):
    if not dbChanged():
        exitNormal(conn, "OK")
    commit = input("commit (y|n): ")
    if commit == "y":
        print("changes committed")
        dbCommit(conn)
        exitNormal(conn, "OK")
    elif commit == "n":
        print("changes NOT committed")
        exitNormal(conn, "OK")
    else:
        print("need y or n")

def mkCfg():
    # if not cfg exist
    # make and write to file
    if os.path.isfile("cfg.json"):
        return
    cfg = {
            "txid": 1,
            "csvLast": None
            }
    putCfg(cfg)

def getCfg():
    with open('cfg.json', 'r') as fh:
        cfg = json.load(fh)
    return cfg

def putCfg(cfg):
    with open('cfg.json', 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=4)

def testGetTxid():
    print(getTxid())
    print(getTxid())
    print(getTxid())
    exitPgm("DBG", -1)

txid = 0

def getTxid():
    global txid
    if txid == 0:
        cfg = getCfg()
        txid = cfg["txid"]
    else:
        txid += 1
    return txid

def putTxid():
    global txid
    cfg = getCfg()
    cfg["txid"] = getTxid()
    putCfg(cfg)

def getConnector(usr, pw, db):
    conn = mariadb.connect(
        user=usr,
        password=pw,
        host="localhost",
        database=db)
    return conn

def getCursor(conn):
    return conn.cursor() 

def dbIsChanged():
    global dbChgAttempt
    dbChgAttempt = True

def dbChanged():
    return dbChgAttempt

def dbOp(cursor, op):
    try:
        cursor.execute(op)
    except mariadb.Error as e:
        exitAbnormal(e)

def dbCommit(conn):
    print("dbCommit")
    conn.commit()
    putTxid()

def dbRollback(conn):
    print("dbRollback")
    conn.rollback()

def mkInsertX(txid, date, amt, ccacct, direct, payee, desc, rid):
    op = ("INSERT INTO transactions "
            "(txid, date,amount,account,direction,payee,descrip,receiptid) VALUES "
            "(" + str(txid) + ",\"" + date + "\"," + amt + "," + ccacct + "," + direct + ",\"" + payee + "\",\"" + desc + "\",\"" + rid + "\");")
    print("op=%s" % op)
    return op

def mkDrX(txid, date, amt, ccacct, payee, desc, rid):
    return mkInsertX(txid, date, amt, ccacct, "1", payee, desc, rid)

def mkCrX(txid, date, amt, ccacct, payee, desc, rid):
    return mkInsertX(txid, date, amt, ccacct, "-1", payee, desc, rid)

def errorReturn(msg):
    print("ERROR:%s" % msg)
    return False

def fixDate(inDate):
        p = inDate.split("/")
        if len(p) != 3:
            print("malformed date: %s" % inDate)
            return "", False
        outDate = p[2] + "-" + p[0] + "-" + p[1]
        return outDate, True

def validateAcct(acct):
    if len(acct) != 3:
        return errorReturn("acct must be 3 digits: %s" % acct)
    if not acct.isdigit():
        return errorReturn("acct must be digits: %s" % acct)
    return True

def getAcct(acctType):
    acct = input("%s account: " % acctType)
    if not validateAcct(acct):
        return "", False
    return acct, True

def chgAddTransaction(cursor):
    print("doInsert")
    date = input("date yyyy-mm-dd: ")
    amt = input("amt: ")
    drAcct, ok = getAcct("debit")
    if not ok:
        return
    crAcct, ok = getAcct("credit")
    if not ok:
        return
    desc = input("desc: ")
    payee = input("payee: ")
    receiptNum = input("receipt # with leading zeros: ")
    if drAcct == crAcct:
        return errorReturn("ERROR: debit account cannot be same as credit account")
    receiptID = ""
    if len(receiptNum) == 3:
        receiptID = "FM-R2023-" + receiptNum
    txid = getTxid()
    drop = mkDrX(txid, date, amt, drAcct, payee, desc, receiptID)
    crop = mkCrX(txid, date, amt, crAcct, payee, desc, receiptID)
    dbIsChanged()
    dbOp(cursor, drop)
    dbOp(cursor, crop)
    # date       | amount   | account | direction | payee | descrip | receiptid

def confirmZero():
    op = ("select "
          "sum(case when direction = 1 then amount end), "
          "sum(case when direction = -1 then amount end) "
          "from transactions;"
         )
    dbOp(dbCursor, op)
    r=[]
    for i in dbCursor:
        print(i)
        r+=i
    if r[0] == r[1]:
        print("DR == CR")
    else:
        print("DR != CR")

def showBalance():
    confirmZero()

def makeDetailedBalanceSheet():
    op = ("select "
                "(account) as a,"
                "name",
                "sum(amount * direction * normal) as balance "
            "from "
                "transactions "
                "left join accounts on a = accounts.number "
            "group by "
                "name "
            "order by "
                "a, "
                "name;"
        )

def showTransactions():
    op = "SELECT * FROM transactions;"
    dbOp(dbCursor, op)
    for i in dbCursor:
        print(i)

def remEnc(inx, dchar):
    if inx[0] == dchar:
        # remove 1st & last chars
        return inx[1:-1]
    return inx

def fixAmt(amt):
    amt = remEnc(amt, "\"")
    amt = remEnc(amt, "(")
    amt = amt.replace(",", "")
    amt = amt.replace("-", "")
    return amt

def chgImportOldCC(cursor):
    print("CCimportOld")
    inFile = input("file path: ")
    print("reading file: %s" % inFile)
    try:
        fh = open(inFile)
    except:
        print("could not open %s" % inFile)
        return
    csvreader = csv.reader(fh)
    for row in csvreader:
        #print(row)
        date, ok = fixDate(row[5])
        if not ok:
            print("import aborted")
            return
        amt = fixAmt(row[7])
        drAcct = row[0]
        crAcct = row[1]
        payee = row[6]
        desc = row[9]
        print("DBG: desc=%s" % desc)
        receiptID = ""
        if len(row[2]) > 0:
            receiptID = "FM-R2023-" + row[2]
        txid = getTxid()
        drop = mkDrX(txid, date, amt, drAcct, payee, desc, receiptID)
        crop = mkCrX(txid, date, amt, crAcct, payee, desc, receiptID)
        dbIsChanged()
        dbOp(cursor, drop)
        dbOp(cursor, crop)

def checkingAccountImportSmallBusBofA(c):
    print("checkingAccountImport")

def csvEngine(rowAct, c, skip):
    inFile = input("file path: ")
    print("reading file: %s" % inFile)
    try:
        fh = open(inFile)
    except:
        print("could not open %s" % inFile)
        return
    csvreader = islice(csv.reader(fh), skip, None)
    #csvreader = islice(csv.DictReader(fh), skip, None)
    i = 1
    for row in csvreader:
        if not rowAct(row, i):
            return
        i += 1

def getInput(user, prompt, required):
    while True:
        reply = input("%s: " % prompt)
        if reply == "q":
            print("%s quit" % user)
            return "", False
        if len(reply) > 0:
            return reply, True
        elif not required:
            return reply, True
        else:
            print("input required")

def showEntry (i, date, amt, payee, desc, rid, dr, cr):
    print("%d. date=%s, amt=%s, payee=%s, desc=%s, receiptID=%s, dr=%s, cr=%s" % 
            (i, date, amt, payee, desc, rid, dr, cr))

def rowActBofAcc(r, i):
    global dbEntries
    print()
    print(r)
    print()
    ccacct = r[1]
    date = r[3]
    payee = r[5]
    amt = fixAmt(r[6])
    if ccacct == "1327":
        cr = "110"
        dr = "210"
        # cc payments - input not needed
        payee = "BofA"
        desc = "CC payment"
        rid = ""
    else:
        # CC purchase
        cr = "210"
        showAcctInfoDR()
        print("\n%d. date=%s, amt=%s, payee=%s, ccacct=%s" % (i, date, amt, payee, ccacct))
        dr, ok = getInput("cc", "debit account", True)
        if not ok:
            return False
        desc, ok = getInput("cc", "description", False)
        if not ok:
            return False
        rid, ok = getInput("cc", "receipt ID", False)
        if not ok:
            return False

    showEntry(i, date, amt, payee, desc, rid, dr, cr)
    ed = {"index":i, "date":date, "amt":amt, "payee":payee, "desc":desc, "rid":rid, "dr":dr, "cr":cr}
    #dbEntries.append((i, date, amt, payee, desc, rid, dr, cr))
    dbEntries.append(ed)
    #print(dbEntries)
    return True

def creditCardImportSmallBusBofA(c):
    print("creditCardImport")
    global dbEntries
    dbEntries = []
    csvEngine(rowActBofAcc, c, 5)
    # review all entries
    for e in dbEntries:
        print()
        print(e)
        txid = getTxid()
        drop = mkDrX(txid, e["date"], e["amt"], e["dr"], e["payee"], e["desc"], e["rid"])
        crop = mkCrX(txid, e["date"], e["amt"], e["cr"], e["payee"], e["desc"], e["rid"])
        print
    # write to file as JSON
    #j = json.dumps(dbEntries, indent=4)
    #print(j)
    # insert into db

def chgAddAccount(dbCursor):
    print("add account")
    name = input("name: ")
    number = input("number: ")
    drcr = input("dr or cr: ")
    if drcr == "dr":
        intDrCr = "1"
    elif drcr == "cr":
        intDrCr = "-1"
    else:
        print("invalid drcr value")
        return
    op = ("INSERT INTO accounts (name, number, normal) VALUES "
            "(\"" + name + "\"," + number + "," + intDrCr + ");")
    print(op)
    dbIsChanged()
    dbOp(dbCursor, op)
    print(dbCursor)

def printAcctInfo(a, drcr):
    for i in a:
        print("%18s, %3s, %2s, %2s" % (i[0], i[1], drcr, i[2]))

def showAcctInfoDR():
    printAcctInfo(drAcct, "DR")

def showAcctInfoCR():
    printAcctInfo(crAcct, "CR")

def showAccounts():
    showAcctInfoDR()
    showAcctInfoCR()

def getAccounts(c):
    global drAcct
    global crAcct

    op = "SELECT * FROM accounts ORDER BY number;"
    dbOp(c, op)
    for i in c:
        if i[2] == 1:
            drAcct.append(i)
        else:
            crAcct.append(i)
    #print(drAcct)
    #print(crAcct)

def readCreds(db):
    with open("creds.csv", "r") as csvfile:
        csvreader = csv.reader(csvfile)

        # skip header
        next(csvreader)

        for row in csvreader:
            if db == row[0]:
                #print(row)
                return row

# --- main ---

print("mariadb frontend for simple accounting, v0.0")

creds = readCreds("testdb")
mkCfg()
#creds = readCreds("fmledger")
#print(creds)
dbConn = getConnector(creds[1], creds[2], creds[0])
dbCursor = getCursor(dbConn)
dbChgAttempt = False
getAccounts(dbCursor)

while True:
    cmd = input("cmd: ")
    if cmd == "h":
        help()
    elif cmd == "q":
        quit(dbConn)
    elif cmd == "ck":
        checkingAccountImportSmallBusBofA(dbCursor)
    elif cmd == "cc":
        creditCardImportSmallBusBofA(dbCursor)
    elif cmd == "inx":
        print("not implemented yet")
    elif cmd == "ccold":
        chgImportOldCC(dbCursor)
    elif cmd == "addac":
        chgAddAccount(dbCursor)
    elif cmd == "shac":
        showAccounts()
    elif cmd == "shbal":
        showBalance()
    elif cmd == "shx":
        showTransactions()
    elif cmd == "addx":
        chgAddTransaction(dbCursor)
    elif cmd == "ct":
        dbCommit(dbConn)
    elif cmd == "rb":
        dbRollback(dbConn)
    else:
        print("cmd not recognized")

# change log

# 2023-08-27, log started, added readCreds(); getting ready to put in GitHub

#select  account, name, sum(amount * direction * normal) as balance  from transactions left join accounts on account = accounts.number group by name order by account;

# TODO chg ccold to csv reader to fix leading dbl quote pblm; add start  of year xacts to ccold csv; chg ccold csv to all
# expenses
