#!/usr/bin/env python3

import os
import sys
import csv
import json
from itertools import islice
from PyPDF2 import PdfReader
import glob

# local imports

import db
import cfg
import ask
import csvop
import stage
import acct
import xact

# globals (eliminate)
#dbEntries=[]
#csvFileList = []
#stagedFileList = []
#invoiceIdList = []

def quitWithMsg(msg):
    print(msg)
    return -1

def proceed():
    reply =  input("proceed(y|n)?: ")
    if reply == "y":
        return True
    return False

def testGetTxid():
    print(getTxid())
    print(getTxid())
    print(getTxid())
    db.exitPgm("DBG", -1)

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
    inFile, ok = csvop.GetFile("ccold")
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
        date, ok = stage.fixDate(row[5])
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
    csvFn, ok = csvop.GetFile(user)
    if not ok:
        return
    # make JSON fn
    baseFn = os.path.basename(csvFn)
    baseFnNoExt = os.path.splitext(baseFn)
    jsonFn = os.path.join(cfg.getStageDir(), baseFnNoExt[0] + ".json")
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

def getStagedFile(user):
    # display list of files in cfg csv dir
    global stagedFileList
    if len(stagedFileList) == 0:
        cfg.getCfg()
        csvFileList = glob.glob(os.path.join(cfg.getStageDir(), "*"))
    return getFileByIndex(csvFileList, user)

def getInvoiceIdDeprecated(user):
    global invoiceIdList
    if len(invoiceIdList) == 0:
        cfg.getCfg()
        invoiceIdList = glob.glob(os.path.join(cfg.getInvoiceDir(), "*pdf"))

    i = 0
    for r in invoiceIdList:
        print("%s (%d)" % (r, i+1))
        i += 1

    # input is number in allowed range, or q=quit/skip
    reply, ok = ask.Ask(user, "invoice ID (number or q=quit)", False)
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
        dr, ok = ask.Ask("cc", "debit account", True)
        if not ok:
            return False
        desc, ok = ask.Ask("cc", "description", False)
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
    csvFn, ok = csvEngine("cc", rowActBofaCC, c, skip=CC_CSV_SKIP)
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
        dr, ok = ask.Ask("ck", "debit account", True)
        if not ok:
            return False
    else:
        cr, ok = ask.Ask("ck", "credit account", True)
        dr = "110"
    desc, ok = ask.Ask("cc", "description", False)
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
    inFile, ok = csvop.GetFile("split")
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
        date, ok = stage.fixDate(tx["date"])
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

def csvEngine2(user, rowMethod, skip):
    csvFn, ok = csvop.GetFile(user)
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

def stageImportCreditCardCsv():
    print("stageCreditCardCsv")
    csvEngine2("ck", stage.AddRowCreditCard, skip=CC_CSV_SKIP)
    return

def stageImportCheckingCsv():
    print("stageCheckingCsv")
    csvEngine2("ck", stage.AddRowChecking, skip=CK_CSV_SKIP)
    return

# --- main ---

print("Open Accounting, v0.1")

cfg.InitCfg()
db.Init()
acct.InitAccounts()

while True:
    if not ask.Cmd():
        sys.exit(0)
