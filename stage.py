import os

import ask
import db
import acct
import cfg
import csv
import csvop
from itertools import islice

# --- private funtions ---

def warn(msg):
    print("\nWARNING:%s\n" % msg)
    return

def checkColumnCount(r, cnt):
    if len(r) != cnt:
        print(r)
        error("column count is %d; expected %d" % (len(r), cnt))
        return False
    return True

def fixDate(inDate):
        p = inDate.split("/")
        if len(p) != 3:
            print("malformed date: %s" % inDate)
            return "", False
        outDate = p[2] + "-" + p[0] + "-" + p[1]
        return outDate, True

def removeChars(s):
    s = s.replace(db.DQ, "")
    return s

def absoluteAmt(amt):
    isnegative = False
    ismoney = False
    if amt[0] == "-":
        isnegative = True
        amt = amt[1:]
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
    return amt, isnegative, ismoney

def moveInvid(fn):
    os.rename(fn, cfg.GetInvoiceUsed())

def inputCrDrDesc(intcr, intdr, desc):
    showAcctListCr=False
    showAcctListDr=True
    cr = str(intcr)
    dr = str(intdr)
    showAcctList=True
    if intcr == 0:
        cr, ok = acct.InputAccountValue("CR", showAcctList)
        if not ok:
            return "",  "",  "", False
        showAcctList=False
    if intdr == 0:
        dr, ok = acct.InputAccountValue("DR", showAcctList)
        if not ok:
            return "",  "",  "", False
    reply = input("description (%s):" % desc)
    if ask.Quit(reply):
        return "",  "", "", False
    else:
        desc = reply
    return cr, dr, desc, True

def guessInvid(date, amt):
    mn = date.strftime("%m")
    yr = date.strftime("%Y")
    #mike@Ununtu-2:~/dev/xygnium$ ls invoices/new/*-03??2023-*-202.00.pdf
    guess = "*-" + mn + "??" + yr + "-*-" + str(amt) + ".pdf"
    print("guess=%s" % guess)
    invid, ok = ask.Ask4FileByIndex("stage", cfg.GetInvoiceDirNew(), guess)
    if not ok:
        return "", False
    invidBasename = os.path.basename(invid)
    print("basename of invid selected = %s" % os.path.basename(invid))
    return invidBasename, True

def chgCrDrDescInvid(r):
    entry= r[0]
    date = r[1]
    amt = r[2]
    dr = r[3]
    cr = r[4]
    desc = r[6]
    invid = r[7]
    invid, ok = guessInvid(date, amt)
    if not ok:
        return
    cr, dr, desc, ok = inputCrDrDesc(cr, dr, desc)
    if not ok:
        return
    #if invidFull != "":
    #    invidUsed = os.path.join(cfg.GetInvoiceDirUsed(), invidBase)
    #    print("mv invidFull=%s invidUsed=%s" % (invidFull, invidUsed))
    #    os.rename(invidFull, invidUsed)
    op = db.MkUpdateStageCrDrDescInvidOp(entry, cr, dr, desc, invid)
    db.TryDbOp(op)
    db.Commit()

def printStageRow(r):
    print("-----------------------------------------")
    print("%12s: %s" % ("entry", r[0]))
    print("%12s: %s" % ("date", r[1]))
    print("%12s: %s" % ("amount", r[2]))
    acct.PrintAccountValue("DR_account", r[3])
    acct.PrintAccountValue("CR_account", r[4])
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

def csvEngine2(tag, rowMethod, skip):
    csvFn, ok = csvop.GetFileByTag("csvEngine2", tag)
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
        if not rowMethod(row):
            return False
        i = i + 1
    return True

# --- public functions ---

def AddRowCreditCard(r):
    # this function is specific to my bank and my account
    # needs to get values from cfg
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
    #if (ccacct == "1327") and (transType == "C"):
    if (ccacct == cfg.GetCcAcct()) and (transType == "C"):
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
    op = db.MkInsertStageOp(date, amt, payee, desc, invid, dr, cr)
    db.dbIsChanged()
    db.TryDbOp(op)
    db.Commit()
    return True

def AddRowChecking(r):
    # this function is specific to my bank and my account
    # needs to get values from cfg
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
    op = db.MkInsertStageOp(date, amt, payee, desc, invid, dr, cr)
    db.TryDbOp(op)
    db.Commit()
    return True

def AuditReview():
    print("stageReview")
    cfg.getCfg()
    op = db.SELECT_STAGE_REVIEW_DATE
    print("op=%s" % op)
    db.TryDbOp(op)
    selectList = db.CursorToList()
    for i in selectList:
        printStageRow(i)
        reply = input("skip=s, quit=q, chg=c, ready=CR: ")
        if reply == "s":
            continue
        elif reply == "q":
            break
        elif reply == "c":
            chgCrDrDescInvid(i)
            print("start review again")
            break
        else:
            op = db.MkUpdateStageStatusOp(i[0], "ready")
            db.TryDbOp(op)
            db.Commit()
    return

def AuditNew():
    print("AuditNew")
    cfg.getCfg()
    op = db.SELECT_STAGE_NEW_DATE
    print("op=%s" % op)
    db.TryDbOp(op)
    selectList = db.CursorToList()
    for i in selectList:
        #print(i)
        printStageRow(i)
        reply = input("skip(y|CR=n|q): ")
        if reply == "y":
            print("skipping")
            continue
        elif reply == "q":
            return
        else:
            chgCrDrDescInvid(i)

def ImportToTransactions():
    print("stageImportToTransactions")
    op = db.SELECT_STAGE_READY_DATE
    print("op=%s" % op)
    db.TryDbOp(op)
    selectList = db.CursorToList()
    for i in selectList:
        #print(i)
        db.PushTxToDb(
                str(i[1]), #date
                str(i[2]), #amt
                str(i[3]), #drAcct
                str(i[4]), #crAcct
                i[5], #payee
                i[6], #descrip
                i[7] #invoiceID
                )
        op = db.MkUpdateStageStatusOp(i[0], "done")
        db.TryDbOp(op)
        db.Commit()

def New():
    print("New")
    date = input("date (mm/dd/yyyy): ")
    date, ok = fixDate(date)
    if not ok:
        return
    amt = input("amount: ")
    amt, isNegative, isMoney = absoluteAmt(amt)
    if not isMoney:
        return
    paidToFrom = input("paid to/from: ")
    cr, dr, desc, ok = inputCrDrDesc(0, 0, "")
    if not ok:
        return
    op = db.MkInsertStageOp(date, amt, paidToFrom, desc, "", dr, cr)
    db.TryDbOp(op)
    db.Commit()

def EditByEntry():
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
    db.TryDbOp(op)
    db.Commit()
    return

def ImportCreditCardCsv():
    print("stageCreditCardCsv")
    csvEngine2("cc", AddRowCreditCard, skip=cfg.GetCcCsvSkip())
    return

def ImportCheckingCsv():
    print("stageCheckingCsv")
    csvEngine2("ck", AddRowChecking, skip=cfg.GetCkCsvSkip())
    return

