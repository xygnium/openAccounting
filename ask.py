import glob
import os

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
    reply, ok = Ask(user, "file (number or q=quit)", False)
    if not ok:
        return "", False
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

