#!/usr/bin/env python3

import os
import sys
import mariadb 
import csv
import json
from itertools import islice
from PyPDF2 import PdfReader
import glob

# local imports

import db

cmds = ["help", "q", "cc-old", "accounts", "ac", "zero", "addac"]

cmdDict = {
        "h": "show all cmds",
        "q": "quit pgm",
        "cc": "make transactions input file from csv file downloaded from BofA credit card account",
        "ck": "make transactions input file from csv file downloaded from BofA checking account",
        "inx": "chg db - import transactions input file",
        "ccold": "chg db - add credit card transactions from modified csv file downloaded from Google Sheets",
        "shbal": "show balance",
        "shac": "show account info",
        "addac": "chg db - add account",
        "addx": "chg db - create and add transaction",
        "shx": "show all transactions",
        "ct": "db commit",
        "rb": "db rollback"
        }

# globals (eliminate)
cfg = {}
drAcct=[]
crAcct=[]
dbEntries=[]
dbChgAttempt = False
txid = 0
csvFileList = []
stagedFileList = []
receiptIdList = []

def help():
    for c in cmdDict:
        print("%10s, %s" % (c, cmdDict[c]))

def quitWithMsg(msg):
    print(msg)
    return -1

def quit(conn):
    if not dbChanged():
        db.exitNormal(conn, "OK")
    commit = input("commit (y|n): ")
    if commit == "y":
        print("changes committed")
        dbCommit(conn)
        db.exitNormal(conn, "OK")
    elif commit == "n":
        print("changes NOT committed")
        db.exitNormal(conn, "OK")
    else:
        print("need y or n")

def mkCfg():
    # if not cfg exist
    # make and write to file
    global cfg, cfgFn
    if os.path.isfile(cfgFn):
        return
    cfg = {
            "db": "testdb",
            "dbuid": "admin",
            "dbpswd": "owl",
            "dbip": None,
            "txid": 1,
            "csvDir": None,
            "receiptDir": None,
            "stageDir": None
            }
    putCfg()

def getCfg():
    global cfg, cfgFn
    with open(cfgFn, 'r') as fh:
        cfg = json.load(fh)

def putCfg():
    global cfg, cfgFn
    with open(cfgFn, 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=4)

def testGetTxid():
    print(getTxid())
    print(getTxid())
    print(getTxid())
    db.exitPgm("DBG", -1)

def getTxid():
    global txid
    if txid == 0:
        getCfg()
        txid = cfg["txid"]
    else:
        txid += 1
    return txid

def putTxid():
    global txid
    getCfg()
    cfg["txid"] = getTxid()
    putCfg()

def getStageDir():
    return cfg["stageDir"]

def getConnector(db, usr, pw):
    conn = mariadb.connect(
        user=usr,
        password=pw,
        host="localhost",
        database=db)
    return conn

def getCursor(conn):
    return conn.cursor() 

def dbChangedReset():
    global dbChgAttempt
    dbChgAttempt = False

def dbIsChanged():
    global dbChgAttempt
    dbChgAttempt = True

def dbChanged():
    return dbChgAttempt

def dbOp(cursor, op):
    try:
        cursor.execute(op)
    except mariadb.Error as e:
        db.exitAbnormal(cursor, e)

def dbCommit(conn):
    print("dbCommit")
    conn.commit()
    putTxid()
    dbChangedReset()

def dbRollback(conn):
    print("dbRollback")
    conn.rollback()
    dbChangedReset()

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

def pushTxToDb(c, date, amt, drAcct, crAcct, payee, desc, receiptID):
    txid = getTxid()
    drop = mkDrX(txid, date, amt, drAcct, payee, desc, receiptID)
    crop = mkCrX(txid, date, amt, crAcct, payee, desc, receiptID)
    dbIsChanged()
    dbOp(c, drop)
    dbOp(c, crop)

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
    pushTxToDb(cursor, date, amt, drAcct, crAcct, payee, desc, receiptID)

def confirmZero(c):
    op = ("select "
          "sum(case when direction = 1 then amount end), "
          "sum(case when direction = -1 then amount end) "
          "from transactions;"
         )
    dbOp(c, op)
    r=[]
    for i in c:
        print(i)
        r+=i
    if r[0] == r[1]:
        print("DR == CR")
    else:
        print("DR != CR")

def makeDetailedBalanceSheet(c):
    op = ("select "
                "account,"
                "name,"
                "sum(amount * direction * normal) as balance "
            "from "
                "transactions "
                "left join accounts on account = accounts.number "
            "group by "
                "account "
            "order by "
                "account;"
        )
    dbOp(c, op)
    #print("%3s  %20s   %8s" % ("No", "Name", "Balance"))
    #for i in c:
    #    print("%3s  %20s   %8s" % (i[0], i[1], i[2]))
    #print
    for i in c:
        print("%s|%s|%s" % (i[0], i[1], i[2]))

def showBalance(c):
    makeDetailedBalanceSheet(c)
    confirmZero(c)

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
    inFile, ok = getCsvFile("ccold")
    if not ok:
        return
    #inFile = input("file path: ")
    print("reading file: %s" % inFile)
    try:
        fh = open(inFile)
    except:
        print("could not open %s" % inFile)
        return
    csvreader = csv.reader(fh)
    for row in csvreader:
        #print(row)
        if row[0] == "210":
            print("skip pmts to CC")
            continue
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
        pushTxToDb(cursor, date, amt, drAcct, crAcct, payee, desc, receiptID)

def csvEngine(user, rowAct, c, skip):
    global dbEntries
    dbEntries = []
    csvFn, ok = getCsvFile(user)
    if not ok:
        return
    # make JSON fn
    baseFn = os.path.basename(csvFn)
    baseFnNoExt = os.path.splitext(baseFn)
    jsonFn = os.path.join(getStageDir(), baseFnNoExt[0] + ".json")
    # if JSON fidbEntries exist; read into dbEntries
    if os.path.isfile(jsonFn):
        with open(jsonFn) as fh:
            dbEntries = json.load(fh)
    else:
        dbEntries = []
    j = len(dbEntries)
    print("dbEntries len = %d" % j)
    # open csv file
    print("reading file: %s" % csvFn)
    try:
        fh = open(csvFn)
    except:
        print("could not open %s" % csvFn)
        return "", False
    # skip top n rows
    csvreader = islice(csv.reader(fh), skip, None)
    #csvreader = islice(csv.DictReader(fh), skip, None)
    # process each row in csv file
    i = 1
    rc = True
    for row in csvreader:
        if j > 0:
            # skip rows already processed
            j -= 1
        elif not rowAct(row, i):
            rc = False
            break
        i += 1
    # write to dbEntries to file as JSON
    with open(jsonFn, 'w', encoding='utf-8') as fh:
        json.dump(dbEntries, fh, ensure_ascii=False, indent=4)
    return csvFn, rc

#def getFileList(fDir, user):

def getFileByIndex(fList, user):
    # prompt user for file selection
    i = 0
    for r in fList:
        print("%s (%d)" % (r, i+1))
        i += 1
    # return file path
    # input is number in allowed range, or q=quit/skip
    reply, ok = getInput(user, "file (number or q=quit)", False)
    if not ok:
        return "", False
    # check number for validity
    select = int(reply) - 1
    if (select >= 0) and (select < i):
        return fList[select], True

    print("number is not in range 1..%d" % i-1)
    return "", False

def getCsvFile(user):
    # display list of files in cfg csv dir
    global csvFileList
    if len(csvFileList) == 0:
        getCfg()
        csvFileList = glob.glob(os.path.join(cfg["csvDir"], "*"))
    return getFileByIndex(csvFileList, user)

def getStagedFile(user):
    # display list of files in cfg csv dir
    global stagedFileList
    if len(stagedFileList) == 0:
        getCfg()
        csvFileList = glob.glob(os.path.join(cfg["stageDir"], "*"))
    return getFileByIndex(csvFileList, user)

def getReceiptId(user):
    global receiptIdList
    if len(receiptIdList) == 0:
        getCfg()
        receiptIdList = glob.glob(os.path.join(cfg["receiptDir"], "*pdf"))

    i = 0
    for r in receiptIdList:
        print("%s (%d)" % (r, i+1))
        i += 1

    # input is number in allowed range, or q=quit/skip
    reply, ok = getInput(user, "receipt ID (number or q=quit)", False)
    if not ok:
        return "", False
    # is reply an index or string?
    if not reply.isdigit():
        return reply, True
    # check number for validity
    select = int(reply) - 1
    if (select >= 0) and (select < i):
        return receiptIdList[select], True

    print("number is not in range 1..%d" % i-1)
    return "", False

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
    print("\n%d. date=%s, amt=%s, payee=%s, desc=%s, receiptID=%s, dr=%s, cr=%s" % 
            (i, date, amt, payee, desc, rid, dr, cr))

def rowActBofaCC(r, i):
    global dbEntries
    print()
    print(r)
    print()
    ccacct = r[1]
    date = r[3]
    payee = r[5]
    amt = fixAmt(r[6])
    if ccacct == "1327":
        # ignore, pmts are reported in checking csv
        return True
    else:
        # CC purchase
        cr = "210"
        print("\n%d. date=%s, amt=%s, payee=%s, ccacct=%s" %
                (i, date, amt, payee, ccacct))
        rid, ok = getReceiptId("cc")
        if not ok:
            return False
        showAcctInfoDR()
        dr, ok = getInput("cc", "debit account", True)
        if not ok:
            return False
        desc, ok = getInput("cc", "description", False)
        if not ok:
            return False

    showEntry(i, date, amt, payee, desc, rid, dr, cr)
    ed = {"index":i,
            "date":date,
            "amt":amt,
            "payee":payee,
            "desc":desc,
            "rid":rid,
            "dr":dr,
            "cr":cr}
    dbEntries.append(ed)
    #print(dbEntries)
    return True

def creditCardImportSmallBusBofA(c):
    print("creditCardImport")
    csvFn, ok = csvEngine("cc", rowActBofaCC, c, skip=5)
    j = json.dumps(dbEntries, indent=4)
    print(j)

def rowActBofaChkAcct(r, i):
    print("%d." % i)
    print(r)
    amt = r[2]
    if len(amt) == 0:
        # ignore line
        print("ignoring entry")
        return True
    showAcctInfoCR()
    showAcctInfoDR()
    if amt[0] == "-":
        amt = amt[1:]
        cr = "110"
        dr, ok = getInput("ck", "debit account", True)
        if not ok:
            return False
    else:
        cr, ok = getInput("ck", "credit account", True)
        dr = "110"
    print("%d. date=%s, payee=%s, amt=%s, cr=%s, dr=%s" % (i, r[0], r[1], amt, cr, dr))
    return True

def checkingAccountImportSmallBusBofA(c):
    print("checkingAccountImport")
    csvEngine("ck", rowActBofaChkAcct, c, skip=7)
    #j = json.dumps(dbEntries, indent=4)
    #print(j)

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
        print("%24s, %3s, %2s, %2s" % (i[0], i[1], drcr, i[2]))

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
    try:
        csvfile = open("creds.csv", "r")
    except:
        db.exitPgm("failed to open cred file", -1)

    csvreader = csv.reader(csvfile)
    # skip header
    next(csvreader)

    for row in csvreader:
        if db == row[0]:
            #print(row)
            return row

def showSyntax(msg):
    print("Usage: oa.py <optional path>/<cfg fn>")
    db.exitPgm(msg, -1)

def getCfgFn():
    if len(sys.argv) != 2:
        showSyntax("missing cfg fn")
    return sys.argv[1]

def runTest():
    while True:
        fn, ok = getReceiptId("test")
        if not ok:
            return
        reader = PdfReader(fn)
        page = reader.pages[0]
        print(page.extract_text())

def inx(cursor):
    # select json file
    fn, ok = getStagedFile("inx")
    if not ok:
        return
    print("transaction file=%s" % fn)
    # read transaction json file
    with open(fn, 'r') as fh:
        txList = json.load(fh)
    # convert each transaction entry into DR and CR ops
    for tx in txList:
        print(tx)
        # run db ops
        date, ok = fixDate(tx["date"])
        if not ok:
            exitAbnormal(c, "bad date format")
        amt = fixAmt(tx["amt"])
        rid = os.path.basename(tx["rid"])
        pushTxToDb(cursor, date, amt, tx["dr"], tx["cr"], tx["payee"], tx["desc"], rid)

# --- main ---

print("mariadb frontend for simple accounting, v0.0")

cfgFn = getCfgFn()
print("cfgFn=%s" % cfgFn)
mkCfg()
getCfg()
#creds = readCreds("testdb")
#creds = readCreds("fmledger")
#print(creds)
#dbConn = getConnector(creds[1], creds[2], creds[0])
dbConn = getConnector(cfg["db"], cfg["dbuid"], cfg["dbpswd"])
dbCursor = getCursor(dbConn)
getAccounts(dbCursor)
#db.exitAbnormal("DBG")

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
        inx(dbCursor)
    elif cmd == "ccold":
        chgImportOldCC(dbCursor)
    elif cmd == "addac":
        chgAddAccount(dbCursor)
    elif cmd == "shac":
        showAccounts()
    elif cmd == "shbal":
        showBalance(dbCursor)
    elif cmd == "shx":
        showTransactions()
    elif cmd == "addx":
        chgAddTransaction(dbCursor)
    elif cmd == "ct":
        dbCommit(dbConn)
    elif cmd == "rb":
        dbRollback(dbConn)
    elif cmd == "test":
        runTest()
    else:
        print("cmd not recognized")

# change log

# 2023-08-27, log started, added readCreds(); getting ready to put in GitHub

#select  account, name, sum(amount * direction * normal) as balance  from transactions left join accounts on account = accounts.number group by name order by account;

# TODO chg ccold to csv reader to fix leading dbl quote pblm; add start  of year xacts to ccold csv; chg ccold csv to all
# expenses
