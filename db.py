import sys
import mariadb 

import cfg

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
SELECT_ALL_ACCTS = "SELECT * FROM accounts ORDER BY number;"
SELECT_STAGE_NEW_DATE = SELECT_ALL_FROM_STAGE + WHERE_STATUS_IS_NEW + ORDER_BY_DATE
SELECT_STAGE_REVIEW_DATE = SELECT_ALL_FROM_STAGE + WHERE_STATUS_IS_REVIEW + ORDER_BY_DATE
SELECT_STAGE_READY_DATE = SELECT_ALL_FROM_STAGE + WHERE_STATUS_IS_READY + ORDER_BY_DATE

# --- private functions ---

def getConnector(db, usr, pw):
    conn = mariadb.connect(
        user=usr,
        password=pw,
        host="localhost",
        database=db)
    return conn

def getCursor(conn):
    return conn.cursor() 

# --- public functions ---

def exitPgm(msg, code):
    print(msg)
    #sys.exit(code)

def exitAbnormal(msg):
    global dbConn, dbCursor, dbChgAttempt
    dbConn.close()
    exitPgm(msg, -1)

def exitNormal(msg):
    global dbConn, dbCursor, dbChgAttempt
    dbConn.close()
    exitPgm(msg, 0)

def Init():
    global dbConn, dbCursor, dbChgAttempt
    dbConn = getConnector(cfg.getDb(), cfg.getDbUid(), cfg.getDbPswd())
    dbCursor = getCursor(dbConn)
    dbChgAttempt = False

def dbChangedReset():
    global dbChgAttempt
    dbChgAttempt = False

def dbIsChanged():
    global dbChgAttempt
    dbChgAttempt = True

def dbChanged():
    return dbChgAttempt

def TryDbOp(op):
    global dbConn, dbCursor, dbChgAttempt
    try:
        dbCursor.execute(op)
    except mariadb.Error as e:
        db.exitAbnormal(e)
    return dbCursor

def CursorToList():
    ilist = []
    for i in dbCursor:
        ilist.append(i)
    return ilist

def Commit():
    print("Commit")
    dbConn.commit()
    dbChangedReset()

def CommitWithTxid():
    print("CommitWithTxid")
    cfg.putTxid()
    Commit()

def dbRollback(conn):
    global dbConn, dbCursor, dbChgAttempt
    print("dbRollback")
    dbConn.rollback()
    dbChangedReset()
    return

def Shutdown():
    if not dbChanged():
        exitNormal("OK")
    else:
        commit = input("commit (y|n): ")
        if commit == "y":
            print("changes committed")
            dbCommit()
            exitNormal("OK")
        elif commit == "n":
            print("changes NOT committed")
            exitNormal("OK")
        else:
            print("need y or n")
    return

def SelectAllAccounts():
    TryDbOp(SELECT_ALL_ACCTS)
    return dbCursor

def MkUpdateStageStatusOp(eid, stat):
    op = ("UPDATE stage "
            "SET status=" + DQ + stat + DQ
            + " WHERE entry=" + str(eid) + SEMI
            )
    print("op=%s" % op)
    return op

def MkUpdateStageCrDrDescInvidOp(eid, cr, dr, desc, invid):
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

def MkUpdateStageInvidOp(eid, invid):
    op = ("UPDATE stage "
            "SET invoiceid=" + DQ + invid + DQ + COMMA
            + "status=" + DQ + "review" + DQ
            + " WHERE entry=" + eid + SEMI
            )
    print("op=%s" % op)
    return op

def MkInsertStageOp(date, amt, payee, desc, invid, dr, cr):
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

def PushTxToDb(date, amt, drAcct, crAcct, payee, desc, invoiceID):
    txid = cfg.getTxid()
    drop = mkDrX(txid, date, amt, drAcct, payee, desc, invoiceID)
    crop = mkCrX(txid, date, amt, crAcct, payee, desc, invoiceID)
    #return
    dbIsChanged()
    TryDbOp(drop)
    TryDbOp(crop)

