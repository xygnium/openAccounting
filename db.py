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
    sys.exit(code)

def exitAbnormal(conn, msg):
    conn.close()
    exitPgm(msg, -1)

def exitNormal(msg):
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
    try:
        dbCursor.execute(op)
    except mariadb.Error as e:
        db.exitAbnormal(cursor, e)
    return dbCursor

def dbCommit():
    print("dbCommit")
    dbConn.commit()
    cfg.putTxid()
    dbChangedReset()

def dbRollback(conn):
    print("dbRollback")
    conn.rollback()
    dbChangedReset()
    return

def Shutdown():
    if not dbChanged():
        exitNormal("OK")
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

def pushTxToDb(c, date, amt, drAcct, crAcct, payee, desc, invoiceID):
    txid = cfg.getTxid()
    drop = mkDrX(txid, date, amt, drAcct, payee, desc, invoiceID)
    crop = mkCrX(txid, date, amt, crAcct, payee, desc, invoiceID)
    #return
    dbIsChanged()
    TryDbOp(drop)
    TryDbOp(crop)

