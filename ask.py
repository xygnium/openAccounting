import glob
import os

# local imports

import db
import cfg
import ask
import csvop
import stage
import acct
import xact

#cmds = ["help", "q", "cc-old", "accounts", "ac", "zero", "addac"]
#        "cc": "make transactions input file from csv file downloaded from BofA credit card account",
#        "ck": "make transactions input file from csv file downloaded from BofA checking account",
#        "inx": "chg db - import transactions input file",
#        "ccold": "chg db - add credit card transactions from modified csv file downloaded from Google Sheets",
#        "split": "split csv file into N files with 4 entries each - needs adjustment for cc vs ck files",

cmdDict = {
        "h": "show all cmds",
        "q": "quit pgm",
        "difcsvck": "compare previous and new checking csv files, find new rows, import to stage table",
        "difcsvcc": "compare previous and new credit card csv files, find new rows, import to stage table",
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

def OaHelp():
    for c in cmdDict:
        print("%10s, %s" % (c, cmdDict[c]))

def Ask(user, prompt, required):
    while True:
        reply = input("\n%s %s: " % (user, prompt))
        print()
        if reply == "q":
            print("%s quit" % user)
            return "", False
        if len(reply) > 0:
            return reply, True
        elif not required:
            return reply, True
        else:
            print("input required")

def Ask4FileByIndex(user, fdir, wild):
    fList = glob.glob(os.path.join(fdir, wild))
    # prompt user for file selection
    i = 0
    for r in fList:
        print("%s (%d)" % (r, i+1))
        i += 1
    reply, ok = Ask(user, "file (number, s=skip, q=quit)", False)
    if not ok:
        return "", False
    if reply =="s":
        return "skip", True
    # check number for validity
    select = int(reply) - 1
    if (select >= 0) and (select < i):
        return fList[select], True

    print("number is not in range 1..%d" % i-1)
    return "", False

def Quit(r):
    if r == "q":
        print("quit")
        return True
    return False

def Cmd():
    cmd = input("cmd: ")
    if cmd == "h":
        OaHelp()
    elif cmd == "q":
        db.Shutdown()
        return False
    elif cmd == "ck":
        checkingAccountImportSmallBusBofA(dbCursor)
    elif cmd == "cc":
        creditCardImportSmallBusBofA(dbCursor)
    elif cmd == "split":
        splitCsv()
    elif cmd == "inx":
        inx(dbCursor)
    elif cmd == "ccold":
        chgImportOldCC(dbCursor)
    elif cmd == "sgcc":
        stageImportCreditCardCsv()
    elif cmd == "sgck":
        stageImportCheckingCsv()
    elif cmd == "sgn":
        stage.New()
    elif cmd == "sge":
        stage.EditByEntry()
    elif cmd == "sgar":
        stage.AuditReview()
    elif cmd == "sgan":
        stage.AuditNew()
    elif cmd == "sg2tx":
        stage.ImportToTransactions()
    elif cmd == "addac":
        chgAddAccount(dbCursor)
    elif cmd == "shac":
        acct.ShowAccounts()
    elif cmd == "shbal":
        xact.ShowBalance()
    elif cmd == "shx":
        xact.ShowTransactions()
    elif cmd == "addx":
        chgAddTransaction(dbCursor)
    elif cmd == "ct":
        dbCommit(dbConn)
        acct.GetAccounts(dbCursor)
    elif cmd == "rb":
        dbRollback(dbConn)
    elif cmd == "difcsvck":
        csvop.SortDiffStage(csvop.CK, cfg.GetCkTag(), cfg.GetCkCsvSkip(), cfg.GetCkCsvSortColumn())
    elif cmd == "difcsvcc":
        csvop.SortDiffStage(csvop.CC, cfg.GetCcTag(), cfg.GetCcCsvSkip(), cfg.GetCcCsvSortColumn())
    elif cmd == "test":
        runTest()
    else:
        print("cmd not recognized")

    return True

