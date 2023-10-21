
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
    if ask.Quit(acct):
        return "", False
    if not validateExistingAcct(acct):
        return "", False
    return acct, True

def InputAccountValue(prompt, showAcctList):
    if showAcctList:
        ShowAccounts()
    return getAcct(prompt)

def PrintAccountValue(label, value):
    acctDesc="invalid"
    if value in acctDict:
        acctDesc = acctDict[value]
    elif value == 0:
        acctDesc = "unassigned"

    print("%12s: %s %s" % (label, value, acctDesc))

# --- public functions ---

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

