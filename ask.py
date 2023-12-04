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

cmdDict = {
        "h": "show all cmds",
        "q": "quit pgm",
        "sgcc": "stage table - import entries from credit card pipe delimited csv file",
        "sgck": "stage table - import entries from checking pipe delimited csv file",
        "sgn": "stage table - create a new entry",
        "sge": "stage table - edit entry description and invoice ID",
        "sgan": "stage table - audit entries where status=new",
        "sgar": "stage table - audit entries where status=review",
        "sg2tx": "stage table - import entries to transaction table where status=ready",
        "shbal": "show balance by accounts",
        "shexp": "show expense summary",
        "shac": "show account info",
        "addac": "add account",
        "dropac": "drop account",
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
        reply = input("\n%s:%s: " % (user, prompt))
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
    elif cmd == "sgcc":
        stage.ImportCreditCardCsv()
    elif cmd == "sgck":
        stage.ImportCheckingCsv()
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
    elif cmd == "dropac":
        acct.DropAccount()
    elif cmd == "addac":
        acct.AddAccount()
    elif cmd == "shac":
        acct.ShowAccounts()
    elif cmd == "shbal":
        xact.ShowBalance()
    elif cmd == "shexp":
        xact.ShowExpenseBalance()
    elif cmd == "shx":
        xact.ShowTransactions()
    elif cmd == "ct":
        dbCommit(dbConn)
        acct.GetAccounts()
    elif cmd == "rb":
        dbRollback(dbConn)
    elif cmd == "initTables":
        db.InitTables()
    elif cmd == "test":
        runTest()
    else:
        print("cmd not recognized")

    return True

