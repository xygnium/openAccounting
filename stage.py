
# --- private funtions ---

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
    s = s.replace(DQ, "")
    return s

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

# --- public funtions ---

def AddRowCreditCard(r, i):
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
    op = mkInsertStageOp(date, amt, payee, desc, invid, dr, cr)
    #dbIsChanged()
    #dbOp(dbCursor, op)
    return True

def AddRowChecking(r, i):
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
    op = mkInsertStageOp(date, amt, payee, desc, invid, dr, cr)
    #dbIsChanged()
    #dbOp(dbCursor, op)
    return True

def AuditReview():
    print("stageReview")
    op = SELECT_ALL_FROM_STAGE + WHERE_STATUS_IS_REVIEW + ORDER_BY_DATE
    print("op=%s" % op)
    dbOp(dbCursor, op)
    selectList = cursorToList()
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
            op = mkUpdateStageStatusOp(i[0], "ready")
            dbOp(dbCursor, op)
            dbConn.commit()
    return

def AuditNew():
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
        else:
            chgCrDrDescInvid(i)

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
    date, ok = stage.fixDate(date)
    if not ok:
        return
    amt = input("amount: ")
    if quit(amt):
        return
    amt, isNegative, isMoney = stage.absoluteAmt(amt)
    if not isMoney:
        return
    paidToFrom = input("paid to/from: ")
    if quit(paidToFrom):
        return
    if len(paidToFrom) == 0:
        error("paid to/from must be entered")
        return
    cr, dr, desc, invid, ok = inputCrDrDescInvid(0, 0, "", "")
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

