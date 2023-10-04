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

DQ = "\""
COMMA = ","
COMMA_DQ = ",\""
DQ_COMMA = "\","
SEMI = ";"
SELECT_ALL_FROM = "SELECT * FROM "
SELECT_ALL_FROM_STAGE = SELECT_ALL_FROM + "stage"
WHERE_STATUS = " WHERE status="
WHERE_STATUS_IS_NEW = WHERE_STATUS + DQ + "new" + DQ
WHERE_STATUS_IS_REVIEW = WHERE_STATUS + DQ + "review" + DQ
WHERE_STATUS_IS_READY = WHERE_STATUS + DQ + "ready" + DQ
WHERE_STATUS_IS_DONE = WHERE_STATUS + DQ + "done" + DQ
ORDER_BY_DATE = " ORDER BY date" + SEMI

#cmds = ["help", "q", "cc-old", "accounts", "ac", "zero", "addac"]

cmdDict = {
        "h": "show all cmds",
        "q": "quit pgm",
        "cc": "make transactions input file from csv file downloaded from BofA credit card account",
        "ck": "make transactions input file from csv file downloaded from BofA checking account",
        "inx": "chg db - import transactions input file",
        "ccold": "chg db - add credit card transactions from modified csv file downloaded from Google Sheets",
        "split": "split csv file into N files with 4 entries each - needs adjustment for cc vs ck files",
        "sgcc": "stage table - import entries from credit card pipe delimited csv file",
        "sgck": "stage table - import entries from checking pipe delimited csv file",
        "sgn": "stage table - create a new entry",
        "sge": "stage table - edit entry description and invoice ID",
        "sgan": "stage table - audit entries where status=new",
        "sgar": "stage table - audit entries where status=review",
        "sg2tx": "stage table - import entries to transaction table where status=ready",
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
acctDict={}
drAcct=[]
crAcct=[]
dbEntries=[]
dbChgAttempt = False
txid = 0
csvFileList = []
stagedFileList = []
invoiceIdList = []

def help():
    for c in cmdDict:
        print("%10s, %s" % (c, cmdDict[c]))

def quitWithMsg(msg):
    print(msg)
    return -1

def shutdown(conn):
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
    return

def proceed():
    reply =  input("proceed(y:N)?: ")
    if reply == "y":
        return True
    return False

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
            "invoiceDir": None,
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
    return

def mkUpdateStageStatusOp(eid, stat):
    op = ("UPDATE stage "
            "SET status=" + DQ + stat + DQ
            + " WHERE entry=" + str(eid) + SEMI
            )
    print("op=%s" % op)
    return op

def mkUpdateStageCrDrDescInvidOp(eid, cr, dr, desc, invid):
    op = ("UPDATE stage "
            + "SET "
            + "CR_account=" + cr + COMMA 
            + "DR_account=" + dr + COMMA 
            + "descrip=" + DQ + desc + DQ + COMMA
            + "invoiceid=" + DQ + invid + DQ + COMMA
            + "status=" + DQ + "review" + DQ
            + " WHERE entry=" + str(eid) + SEMI
            )
    print("op=%s" % op)
    return op

def mkUpdateStageInvidOp(eid, invid):
    op = ("UPDATE stage "
            "SET invoiceid=" + DQ + invid + DQ + COMMA
            + "status=" + DQ + "review" + DQ
            + " WHERE entry=" + eid + SEMI
            )
    print("op=%s" % op)
    return op

def mkInsertStageOp(date, amt, payee, desc, invid, dr, cr):
    op = ("INSERT INTO stage  "
            "(date, amount, DR_account, CR_account, payee_payer, descrip, invoiceid, status) VALUES "
            "("
            + DQ + date + DQ + COMMA
            + amt + COMMA
            + dr + COMMA
            + cr + COMMA
            + DQ + payee + DQ + COMMA
            + DQ + desc + DQ + COMMA
            + DQ + invid + DQ + COMMA
            + DQ + "new" + DQ + ");"
            )
    print("op=%s" % op)
    return op

def mkInsertX(txid, date, amt, acct, direct, payee, desc, invid):
    op = ("INSERT INTO transactions "
            "(txid, date,amount,account,direction,payee,descrip,invoiceid) VALUES "
            "(" + str(txid) + ",\"" + date + "\"," + amt + "," + acct + "," + direct + ",\"" + payee + "\",\"" + desc + "\",\"" + invid + "\");")
    print("op=%s" % op)
    return op

def mkDrX(txid, date, amt, acct, payee, desc, invid):
    return mkInsertX(txid, date, amt, acct, "1", payee, desc, invid)

def mkCrX(txid, date, amt, acct, payee, desc, invid):
    return mkInsertX(txid, date, amt, acct, "-1", payee, desc, invid)

def errorReturn(msg):
    error(msg)
    return False

def fixDate(inDate):
        p = inDate.split("/")
        if len(p) != 3:
            print("malformed date: %s" % inDate)
            return "", False
        outDate = p[2] + "-" + p[0] + "-" + p[1]
        return outDate, True

def showAccounts():
    drLen = len(drAcct)
    crLen = len(crAcct)
    if drLen > crLen:
        lineCnt = drLen
    else:
        lineCnt = crLen

    i = 0
    dri = 0
    cri = 0
    typeDR = "DR"
    typeCR = "CR"
    while i < lineCnt:
        if dri < drLen:
            drLine = drAcct[i]
        else:
            drLine = ("", "", "")
            typeDR = ""
        if cri < crLen:
            crLine = crAcct[i]
        else:
            crLine = ("", "", "")
            typeCR = ""

        print("%24s  %3s  %2s  %2s    %24s  %3s  %2s  %2s" % 
                (drLine[0], drLine[1], typeDR, drLine[2],
                 crLine[0], crLine[1], typeCR, crLine[2]))

        i = i + 1
        dri = dri + 1
        cri = cri + 1

def getAccounts(c):
    global acctDict
    global drAcct
    global crAcct

    acctDict={}
    drAcct=[]
    crAcct=[]
    op = "SELECT * FROM accounts ORDER BY number;"
    dbOp(c, op)
    for i in c:
        acctDict[i[1]] = i[0]
        if i[2] == 1:
            drAcct.append(i)
        else:
            crAcct.append(i)
    #print(drAcct)
    #print(crAcct)
    #print(acctDict)

def validateExistingAcct(acct):
    if not validateNewAcct(acct):
        return False
    print("acct=%s, dict entry=%s" % (acct, acctDict[int(acct)]))
    if not int(acct) in acctDict:
        return errorReturn("account value (%s) not in list" % acct)
    return True
    
def validateNewAcct(acct):
    if not acct.isdigit():
        return errorReturn("acct must be digits: %s" % acct)
    elif len(acct) != 3:
        return errorReturn("acct must be 3 digits: %s" % acct)
    elif acct == "000":
        return errorReturn("acct 000 is reserved")
    return True

def getAcct(prompt):
    acct = input("%s account: " % prompt)
    if quit(acct):
        return "", False
    if not validateExistingAcct(acct):
        return "", False
    return acct, True

def inputAccountValue(prompt, showAcctList):
    if showAcctList:
        showAccounts()
    return getAcct(prompt)

def pushTxToDb(c, date, amt, drAcct, crAcct, payee, desc, invoiceID):
    txid = getTxid()
    drop = mkDrX(txid, date, amt, drAcct, payee, desc, invoiceID)
    crop = mkCrX(txid, date, amt, crAcct, payee, desc, invoiceID)
    #return
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
    invoiceNum = input("invoice # with leading zeros: ")
    if drAcct == crAcct:
        return errorReturn("ERROR: debit account cannot be same as credit account")
    invoiceID = ""
    if len(invoiceNum) == 3:
        invoiceID = "FM-R2023-" + invoiceNum
    pushTxToDb(cursor, date, amt, drAcct, crAcct, payee, desc, invoiceID)

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

def removeChars(s):
    s = s.replace(DQ, "")
    return s

def fixAmt(amt):
    amt = remEnc(amt, "\"")
    amt = remEnc(amt, "(")
    amt = amt.replace(",", "")
    amt = amt.replace("-", "")
    return amt

def absoluteAmt(amt):
    isnegative = False
    ismoney = False
    parts = amt.split(".")
    plen = len(parts)
    if ((plen < 1) or (plen > 2)):
        print("amount is malformed: %s" % amt)
        return 0, isnegative, ismoney
    dollars = parts[0]
    if not dollars.isdecimal():
        print("dollar amount is not a number: %s" % dollars)
    if plen == 2:
        cents = parts[1]
        if not cents.isdecimal():
            print("cents amount is not a number: %s" % cents)
            return 0, isnegative, ismoney
        if len(cents) > 2:
            print("cents amount is not a two digit number: %s" % cents)
            return 0, isnegative, ismoney
    ismoney = True
    if amt[0] == "-":
        isnegative = True
        amt = amt[1:]
    return amt, isnegative, ismoney

def chgImportOldCC(cursor):
    print("CCimportOld")
    inFile, ok = getCsvFile("ccold")
    if not ok:
        return
    #inFile = input("file path: ")
    print("reading file: %s" % inFile)
    try:
        fh = open(inFile, newline='')
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
        invoiceID = ""
        if len(row[2]) > 0:
            invoiceID = "FM-R2023-" + row[2]
        pushTxToDb(cursor, date, amt, drAcct, crAcct, payee, desc, invoiceID)

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
        fh = open(csvFn, newline='')
    except:
        print("could not open %s" % csvFn)
        return "", False
    # skip top n rows
    csvreader = islice(csv.reader(fh, delimiter="|"), skip, None)
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
        #csvFileList = glob.glob(os.path.join(cfg["csvDir"], "fm*"))
    return getFileByIndex(csvFileList, user)

def getStagedFile(user):
    # display list of files in cfg csv dir
    global stagedFileList
    if len(stagedFileList) == 0:
        getCfg()
        csvFileList = glob.glob(os.path.join(cfg["stageDir"], "*"))
    return getFileByIndex(csvFileList, user)

def getInvoiceId(user):
    global invoiceIdList
    if len(invoiceIdList) == 0:
        getCfg()
        invoiceIdList = glob.glob(os.path.join(cfg["invoiceDir"], "*pdf"))

    i = 0
    for r in invoiceIdList:
        print("%s (%d)" % (r, i+1))
        i += 1

    # input is number in allowed range, or q=quit/skip
    reply, ok = getInput(user, "invoice ID (number or q=quit)", False)
    if not ok:
        return "", False
    # is reply an index or string?
    if not reply.isdigit():
        return reply, True
    # check number for validity
    select = int(reply) - 1
    if (select >= 0) and (select < i):
        return invoiceIdList[select], True

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

def showEntry (i, date, amt, payee, desc, invid, dr, cr):
    print("\n%d. date=%s, amt=%s, payee=%s, desc=%s, invoiceID=%s, dr=%s, cr=%s" % 
            (i, date, amt, payee, desc, invid, dr, cr))

def rowActBofaCC(r, i):
    global dbEntries
    print()
    print(r)
    if not verifyListLen("BofA CC csv row", r, 11):
        return False
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
        invid, ok = getInvoiceId("cc")
        if not ok:
            return False
        showAcctInfoDR()
        dr, ok = getInput("cc", "debit account", True)
        if not ok:
            return False
        desc, ok = getInput("cc", "description", False)
        if not ok:
            return False

    showEntry(i, date, amt, payee, desc, invid, dr, cr)
    ed = {"index":i,
            "date":date,
            "amt":amt,
            "payee":payee,
            "desc":desc,
            "invid":invid,
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

def verifyListLen(label, r, expLen):
    print(r)
    listLen = len(r)
    print("%s len=%d, expected=%d" % (label, listLen, expLen))
    if listLen != expLen:
        print("ERROR:%s len not %d" % (label, expLen))
        return False
    return True

def rowActBofaChkAcct(r, i):
    print("%d." % i)
    if not verifyListLen("BofA Checking csv row", r, 4):
        return False
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
    desc, ok = getInput("cc", "description", False)
    if not ok:
        return False
    print("%d. date=%s, payee=%s, amt=%s, desc=%s, cr=%s, dr=%s" % (i, r[0], r[1], amt, desc, cr, dr))
    date=r[0]
    payee=r[1][:64]
    invid=""
    showEntry(i, date, amt, payee, desc, invid, dr, cr)
    ed = {"index":i,
            "date":date,
            "amt":amt,
            "payee":payee,
            "desc":desc,
            "invid":invid,
            "dr":dr,
            "cr":cr}
    dbEntries.append(ed)
    return True

def checkingAccountImportSmallBusBofA(c):
    print("checkingAccountImport")
    csvEngine("ck", rowActBofaChkAcct, c, skip=0)
    j = json.dumps(dbEntries, indent=4)
    print(j)

def chgAddAccount(dbCursor):
    print("add account")
    name = input("name: ")
    number = input("number: ")
    if not validateNewAcct(number):
        return
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

def readCreds(db):
    try:
        csvfile = open("creds.csv", "r", newline='')
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

lc = 0
fc = 0
def mkSplitFile(fn, line, linesPerFile):
    global lc, fc
    basefn = os.path.basename(fn)
    fndir = os.path.dirname(fn)
    lfn = os.path.join(fndir, str(fc) + basefn)
    if lc == 0:
        if os.path.isfile(lfn):
            os.remove(lfn)
    sline = ','.join(line) + "\n"
    with open(lfn, "a") as fh:
        fh.write(sline)
    lc = lc + 1
    if lc == linesPerFile:
        lc = 0
        fc = fc + 1

def splitCsv():
    print("split")
    inFile, ok = getCsvFile("split")
    if not ok:
        return
    print("reading file: %s" % inFile)
    try:
        fh = open(inFile, "r", newline='')
    except:
        print("could not open %s" % inFile)
        return
    # skip top n rows
    skip=8
    linesPerFile=4
    csvreader = islice(csv.reader(fh), skip, None)
    for row in csvreader:
        mkSplitFile(inFile, row, linesPerFile)

def runTest():
    while True:
        fn, ok = getInvoiceId("test")
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
        invid = os.path.basename(tx["invid"])
        payee =  tx["payee"][:64]
        pushTxToDb(cursor, date, amt, tx["dr"], tx["cr"], payee, tx["desc"], invid)
    return

def error(msg):
    print("ERROR:" + msg)
    return

def warn(msg):
    print("WARNING:" + msg)
    return

def checkColumnCount(r, cnt):
    if len(r) != cnt:
        print(r)
        error("column count is %d; expected %d" % (len(r), cnt))
        return False
    return True

def csvEngine2(user, rowMethod, skip):
    csvFn, ok = getCsvFile(user)
    if not ok:
        return False
    # open csv file
    print("reading file: %s" % csvFn)
    try:
        fh = open(csvFn, newline='')
    except:
        print("could not open %s" % csvFn)
        return False
    # skip top n rows
    csvreader = islice(csv.reader(fh, delimiter="|"), skip, None)
    #csvreader = islice(csv.DictReader(fh), skip, None)
    i = 1
    for row in csvreader:
        if not rowMethod(row, i):
            return False
        i = i + 1
    return True

def rowStageCreditCardCsv(r, i):
    cfgColumnCount = 11
    if not checkColumnCount(r, cfgColumnCount):
        return False
    ccacct = r[1]
    date = r[3]
    date, ok = fixDate(date)
    if not ok:
        return False
    payee = removeChars(r[5][:64])
    transType = r[9]
    if (ccacct == "1327") and (transType == "C"):
        print(r)
        warn("ignoring row; pmt to cc are recorded in checking account")
        return True
    amt, isNegative, isMoney = absoluteAmt(r[6])
    if not isMoney:
        return False
    if isNegative:
        cr = "000"
        dr = "210"
    else:
        cr = "210"
        dr = "000"
    invid = ""
    desc = ""
    showEntry(i, date, amt, payee, desc, invid, dr, cr)
    op = mkInsertStageOp(date, amt, payee, desc, invid, dr, cr)
    dbIsChanged()
    dbOp(dbCursor, op)
    return True

def stageImportCreditCardCsv():
    print("stageCreditCardCsv")
    csvEngine2("ck", rowStageCreditCardCsv, skip=5)
    return

def rowStageCheckingCsv(r, i):
    cfgColumnCount = 4
    if not checkColumnCount(r, cfgColumnCount):
        return False
    amt = r[2]
    if len(amt) == 0:
        print(r)
        warn("ignoring null amount entry")
        return True
    amt, isNegative, isMoney = absoluteAmt(amt)
    if not isMoney:
        return False
    if isNegative:
        cr = "110"
        dr = "000"
    else:
        cr = "000"
        dr = "110"
    desc = ""
    date=r[0]
    date, ok = fixDate(date)
    if not ok:
        return False
    payee = removeChars(r[1][:64])
    invid = ""
    showEntry(i, date, amt, payee, desc, invid, dr, cr)
    op = mkInsertStageOp(date, amt, payee, desc, invid, dr, cr)
    dbIsChanged()
    dbOp(dbCursor, op)
    return True

def stageImportCheckingCsv():
    print("stageCheckingCsv")
    csvEngine2("ck", rowStageCheckingCsv, skip=8)
    return

def printAccountValue(label, value):
    acctDesc="invalid"
    if value in acctDict:
        acctDesc = acctDict[value]
    elif value == 0:
        acctDesc = "unassigned"

    print("%12s: %s %s" % (label, value, acctDesc))

def printStageRow(r):
    print("-----------------------------------------")
    print("%12s: %s" % ("entry", r[0]))
    print("%12s: %s" % ("date", r[1]))
    print("%12s: %s" % ("amount", r[2]))
    printAccountValue("DR_account", r[3])
    printAccountValue("CR_account", r[4])
    print("%12s: %s" % ("payee_payer", r[5]))
    print("%12s: %s" % ("descrip", r[6]))
    print("%12s: %s" % ("invoiceid", r[7]))
    print("%12s: %s" % ("status", r[8]))
#      entry: 441
#       date: 2022-12-30
#     amount: 500.00
# DR_account: 0
# CR_account: 110
#payee_payer: Zelle Transfer Conf# d94mvrik6; Mueller, Gabriel
#    descrip: 
#  invoiceid: 
#     status: delete

def cursorToList():
    ilist = []
    for i in dbCursor:
        ilist.append(i)
    return ilist

def stageAuditReview():
    print("stageReview")
    op = SELECT_ALL_FROM_STAGE + WHERE_STATUS_IS_REVIEW + ORDER_BY_DATE
    print("op=%s" % op)
    dbOp(dbCursor, op)
    selectList = cursorToList()
    for i in selectList:
        printStageRow(i)
        reply = input("change status to ready? (y/n/q CR=n): ")
        if reply == "y":
            op = mkUpdateStageStatusOp(i[0], "ready")
            dbOp(dbCursor, op)
            dbConn.commit()
        elif reply == "q":
            break
    return

def quit(r):
    if r == "q":
        return True
    return False

def inputCrDrDescInvid(cr, dr, desc, invid):
    showAcctListCr=False
    showAcctListDr=True
    if cr == "0":
        showAcctListCr=True
        cr, ok = inputAccountValue("CR", showAcctListCr)
        if not ok:
            return "",  "",  "",  "", False
    if dr == "0":
        if showAcctListCr:
            showAcctListDr=False
        dr, ok = inputAccountValue("DR", showAcctListDr)
        if not ok:
            return "",  "",  "",  "", False
    reply = input("description (%s):" % desc)
    if quit(reply):
        return "",  "",  "",  "", False
    elif len(reply) > 0:
        desc = reply
    reply = input("invoice id (%s): " % invid)
    if quit(reply):
        return "",  "",  "",  "", False
    elif len(reply) > 0:
        invid = reply
    return cr, dr, desc, invid, True

def stageAuditNew():
    print("stageAuditNew")
    op = SELECT_ALL_FROM_STAGE + WHERE_STATUS_IS_NEW + ORDER_BY_DATE
    print("op=%s" % op)
    dbOp(dbCursor, op)
    selectList = cursorToList()
    for i in selectList:
        #print(i)
        printStageRow(i)
        reply = input("skip(y|CR=n|q): ")
        if reply == "y":
            print("skipping")
            continue
        elif reply == "q":
            return
        dr = str(i[3])
        cr = str(i[4])
        cr, dr, desc, invid, ok = inputCrDrDescInvid(cr, dr, i[6], i[7])
        if not ok:
            return
        op = mkUpdateStageCrDrDescInvidOp(i[0], cr, dr, desc, invid)
        dbOp(dbCursor, op)
        dbConn.commit()

def stageImportToTransactions():
    print("stageImportToTransactions")
    op = SELECT_ALL_FROM_STAGE + WHERE_STATUS_IS_READY + ORDER_BY_DATE
    print("op=%s" % op)
    dbOp(dbCursor, op)
    selectList = cursorToList()
    for i in selectList:
        #print(i)
        pushTxToDb(dbCursor,
                str(i[1]), #date
                str(i[2]), #amt
                str(i[3]), #drAcct
                str(i[4]), #crAcct
                i[5], #payee
                i[6], #descrip
                i[7] #invoiceID
                )
        op = mkUpdateStageStatusOp(i[0], "done")
        dbOp(dbCursor, op)
        dbConn.commit()

def stageNew():
    print("stageNew")
    date = input("date (mm/dd/yyyy): ")
    if quit(date):
        return
    date, ok = fixDate(date)
    if not ok:
        return
    amt = input("amount: ")
    if quit(amt):
        return
    amt, isNegative, isMoney = absoluteAmt(amt)
    if not isMoney:
        return
    paidToFrom = input("paid to/from: ")
    if quit(paidToFrom):
        return
    if len(paidToFrom) == 0:
        error("paid to/from must be entered")
        return
    cr, dr, desc, invid, ok = inputCrDrDescInvid("0", "0", "", "")
    if not ok:
        return
    op = mkInsertStageOp(date, amt, paidToFrom, desc, invid, dr, cr)
    # put stage row
    dbOp(dbCursor, op)
    dbConn.commit()

def stageEditByEntry():
    print("stageEdit")
    # get stage row by entry
    entry = input("stage table entry number: ")
    op = ("SELECT * FROM stage WHERE entry = " + entry + SEMI)
    print("op=%s" % op)
    dbOp(dbCursor, op)
    for i in dbCursor:
        print(i)
        for f in i:
            print(f)
    # get new info
    invid = input("invid: ")
    #status = "review"
    op = mkUpdateStageInvidOp(entry, invid)
    # put stage row
    dbOp(dbCursor, op)
    dbConn.commit()
    return

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
        shutdown(dbConn)
    elif cmd == "ck":
        checkingAccountImportSmallBusBofA(dbCursor)
    elif cmd == "cc":
        creditCardImportSmallBusBofA(dbCursor)
    elif cmd == "inx":
        inx(dbCursor)
    elif cmd == "ccold":
        chgImportOldCC(dbCursor)
    elif cmd == "sgcc":
        stageImportCreditCardCsv()
    elif cmd == "sgck":
        stageImportCheckingCsv()
    elif cmd == "sgn":
        stageNew()
    elif cmd == "sge":
        stageEditByEntry()
    elif cmd == "sgar":
        stageAuditReview()
    elif cmd == "sgan":
        stageAuditNew()
    elif cmd == "sg2tx":
        stageImportToTransactions()
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
        getAccounts(dbCursor)
    elif cmd == "rb":
        dbRollback(dbConn)
    elif cmd == "split":
        splitCsv()
    elif cmd == "test":
        runTest()
    else:
        print("cmd not recognized")

# change log

# 2023-08-27, log started, added readCreds(); getting ready to put in GitHub

#select  account, name, sum(amount * direction * normal) as balance  from transactions left join accounts on account = accounts.number group by name order by account;

# TODO chg ccold to csv reader to fix leading dbl quote pblm; add start  of year xacts to ccold csv; chg ccold csv to all
# expenses
