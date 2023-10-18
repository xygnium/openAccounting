import csv
#import operator
from itertools import islice
from datetime import datetime

import cfg
import ask
import stage

CK="checking"
CC="creditcard"

# --- private functions ---

def getCsvReader(user, skip, fn):
    # open csv file
    print("reading file: %s" % fn)
    try:
        fh = open(fn, newline='')
    except:
        print("could not open %s" % fn)
        return False
    # skip top n rows
    csvreader = islice(csv.reader(fh, delimiter="|"), skip, None)
    #csvreader = islice(csv.DictReader(fh), skip, None)
    return csvreader

def sortedCsvList(fn, skip, column):
    print("sortedCsvList")
    csvRdr = getCsvReader("sortedCsvList", skip, fn)
    sortedlist = sorted(csvRdr, key=lambda row: datetime.strptime(row[column], "%m/%d/%Y"), reverse=False)
    #sortedlist = sorted(csvRdr, key=operator.itemgetter(0), reverse=False)
    print()
    i = 0
    for r in sortedlist:
        rstr = " | ".join(r)
        print("%3d. %.150s" %(i, rstr))
        i +=1
    print()
    return sortedlist
    
def getFileByTag(user, tag):
    # display list of files in cfg csv dir
    fnWildcard = "*%s*" % tag
    return ask.Ask4FileByIndex(user, cfg.getCsvDir(), fnWildcard)

# --- public functions ---

def GetFile(user):
    # display list of files in cfg csv dir
    return ask.Ask4FileByIndex(user, cfg.getCsvDir(), "*")

def SortDiffStage(user, tag, skip, sortColumn):
    userOld = "%s - previous csv" % user
    csvFnOld, ok = getFileByTag(userOld, tag)
    if not ok:
        return False
    csvListSortedOld = sortedCsvList(csvFnOld, skip, sortColumn)

    userNew = "%s - current csv" % user
    csvFnNew, ok = getFileByTag(userNew, tag)
    if not ok:
        return False
    csvListSortedNew = sortedCsvList(csvFnNew, skip, sortColumn)

    # find where old and new overlap begins

    startRow = csvListSortedNew[0]
    iold = 0
    foundOverlapStart = False
    for ro in csvListSortedOld:
        if startRow == ro:
            foundOverlapStart = True
            print("\nfound start of where new overlaps old at iold=%d\n" % iold)
            break
        iold +=1

    if not foundOverlapStart:
        print("\ndid not find start of where new overlaps old\n")
        return

    inew = 0
    while (inew < len(csvListSortedNew)) and (iold < len(csvListSortedOld)):
        print("inew=%3d: %.150s" % (inew, " | ".join(csvListSortedNew[inew])))
        print("iold=%3d: %.150s" % (iold, " | ".join(csvListSortedOld[iold])))
        if csvListSortedNew[inew] != csvListSortedOld[iold]:
            print("\nfound end of where new overlaps old at inew=%d and iold=%d\n" % (inew, iold))
            break
        inew +=1
        iold +=1
        if inew >= len(csvListSortedNew):
            print("\nall rows in new overlap old - terminating\n")
            return
        if iold >= len(csvListSortedOld):
            print("\nfound end of where new overlaps old at inew=%d and iold=end\n" % inew)

    print()
    print("new csv rows:")
    print()
    for r in csvListSortedNew[inew:]:
        print("%.150s" % " | ".join(r))

    # add new csv rows to stage table

    reply, ok = ask.Ask(user, "add new csv rows to stage table? (y|n)", True)
    if (not ok) or (reply != "y"):
        print("terminated, reply=%s" % reply)
        return

    for r in csvListSortedNew[inew:]:
        print("%.150s" % " | ".join(r))
        if user == CK:
            if not stage.AddRowChecking(r):
                return
        elif user == CC:
            if not stage.AddRowCreditCard(r):
                return
        else:
            print("user not recognized: %s" % user)
            return


    return
