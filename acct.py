
import ask
import db

acctDict={}
drAcct=[]
crAcct=[]

# --- private functions ---

def errorReturn(msg):
    error(msg)
    return False

def validateExistingAcct(acct):
    if not validateNewAcct(acct):
        return False
    if not int(acct) in acctDict:
        return errorReturn("account value (%s) not in list" % acct)
    print("acct=%s, dict entry=%s" % (acct, acctDict[int(acct)]))
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
    if ask.Quit(acct):
        return "", False
    if not validateExistingAcct(acct):
        return "", False
    return acct, True

# --- public functions ---

def InputAccountValue(prompt, showAcctList):
    if showAcctList:
        ShowAccounts()
    return getAcct(prompt)

def PrintAccountValue(label, value):
    acctDesc="invalid"
    if int(value) in acctDict:
        acctDesc = acctDict[int(value)]
    elif value == 0:
        acctDesc = "unassigned"

    print("%12s: %s %s" % (label, value, acctDesc))

def InitAccounts():
    # load lists of accounts
    global acctDict
    global drAcct
    global crAcct

    acctDict={}
    drAcct=[]
    crAcct=[]
    c = db.SelectAllAccounts()
    for i in c:
        acctDict[i[1]] = i[0]
        if i[2] == 1:
            drAcct.append(i)
        else:
            crAcct.append(i)
    #print(drAcct)
    #print(crAcct)
    #print(acctDict)

def ShowAccounts():
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

def DropAccount():
    an, ok = InputAccountValue("drop acct", showAcctList=True)
    if not ok:
        return
    PrintAccountValue("dropping account", an)
    op = ("DELETE FROM accounts WHERE number=" + an)
    print("op=%s" % op)
    db.PushChange(op)
    db.Commit()

def AddAccount():
    name, ok = ask.Ask("AddAccount", "name", required=True)
    if not ok:
        return
    number, ok = ask.Ask("AddAccount", "number", required=True)
    if not ok:
        return
    if not validateNewAcct(number):
        return
    drcr, ok = ask.Ask("AddAccount", "account type (dr/cr)", required=True)
    if not ok:
        return
    if drcr == "dr":
        intDrCr = "1"
    elif drcr == "cr":
        intDrCr = "-1"
    else:
        print("invalid drcr value")
        return
    op = ("INSERT INTO accounts (name, number, normal) VALUES "
            "(\"" + name + "\"," + number + "," + intDrCr + ");")
    db.PushChange(op)
    db.Commit()

