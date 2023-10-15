
import db

# --- private functions ---

# --- public functions ---

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

def confirmZero():
    op = ("SELECT "
          "sum(case when direction = 1 then amount end), "
          "sum(case when direction = -1 then amount end) "
          "FROM transactions;"
         )
    c = db.TryDbOp(op)
    r=[]
    for i in c:
        print(i)
        r+=i
    if r[0] == r[1]:
        print("DR == CR")
    else:
        print("DR != CR")

def makeDetailedBalanceSheet():
    op = ("SELECT "
                "account,"
                "name,"
                "sum(amount * direction * normal) as balance "
            "FROM "
                "transactions "
                "left join accounts on account = accounts.number "
            "GROUP BY "
                "account "
            "ORDER BY "
                "account;"
        )
    c = db.TryDbOp(op)
    #print("%3s  %20s   %8s" % ("No", "Name", "Balance"))
    #for i in c:
    #    print("%3s  %20s   %8s" % (i[0], i[1], i[2]))
    #print
    for i in c:
        print("%s|%s|%s" % (i[0], i[1], i[2]))

def ShowBalance():
    makeDetailedBalanceSheet()
    confirmZero()

def showTransactions():
    op = "SELECT * FROM transactions;"
    dbOp(dbCursor, op)
    for i in dbCursor:
        print(i)

