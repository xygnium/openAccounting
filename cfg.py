import sys
import os
import json

GLOBAL_cfgFn = ""
GLOBAL_cfg = {}
GLOBAL_txid = 0

# --- private functions ---

def mkCfg():
    global GLOBAL_cfg, GLOBAL_cfgFn
    if os.path.isfile(GLOBAL_cfgFn):
        return

    # if not cfg exist
    # make and write to file
    GLOBAL_cfg = {
            "db": None,
            "dbuid": "admin",
            "dbpswd": None,
            "dbip": None,
            "tblAccountsInit": None,
            "txid": 0,
            "csvDirNew": None,
            "csvDirUsed": None,
            "invoiceDirNew": None,
            "invoiceDirUsed": None,
            "checkingTag": "ck",
            "checkingCsvSortColumn": 0,
            "checkingCsvSkip": 8,
            "creditCardTag": "cc",
            "creditCardAcct": None,
            "creditCardCsvSortColumn": 3,
            "creditCardCsvSkip": 5,
            "stageDir": None
            }
    putCfg()
    showSyntax("created %s; edit and restart program" % GLOBAL_cfgFn)

def showSyntax(msg):
    print("ERROR:%s" % msg)
    print("Usage: oa.py <optional path>/<cfg fn>")
    sys.exit(-1)

def getCfgFn():
    if len(sys.argv) != 2:
        showSyntax("missing cfg fn")
    cfgfn = sys.argv[1]
    if not os.path.isfile(cfgfn):
        print("file does not exist; creating: %s" % cfgfn)
    return cfgfn

def getCfg():
    global GLOBAL_cfg, GLOBAL_cfgFn
    with open(GLOBAL_cfgFn, 'r') as fh:
        GLOBAL_cfg = json.load(fh)

def putCfg():
    global GLOBAL_cfg, GLOBAL_cfgFn
    with open(GLOBAL_cfgFn, 'w', encoding='utf-8') as fh:
        json.dump(GLOBAL_cfg, fh, ensure_ascii=False, indent=4)

# --- public functions ---

def InitCfg():
    global GLOBAL_cfgFn, GLOBAL_txid
    GLOBAL_cfgFn = getCfgFn()
    print("GLOBAL_cfgFn=%s" % GLOBAL_cfgFn)
    mkCfg()
    getCfg()
    GLOBAL_txid = GLOBAL_cfg["txid"]

def getTxid():
    global GLOBAL_txid
    GLOBAL_txid += 1
    return GLOBAL_txid

def putTxid():
    global GLOBAL_txid
    getCfg()
    GLOBAL_cfg["txid"] = GLOBAL_txid
    putCfg()

def getDb():
    return GLOBAL_cfg["db"]

def getDbUid():
    return GLOBAL_cfg["dbuid"]

def getDbPswd():
    return GLOBAL_cfg["dbpswd"]

def GetTblAccountsInit():
    return GLOBAL_cfg["tblAccountsInit"]

def GetCsvDirNew():
    return GLOBAL_cfg["csvDirNew"]

def GetCsvDirUsed():
    return GLOBAL_cfg["csvDirUsed"]

def GetInvoiceDirNew():
    return GLOBAL_cfg["invoiceDirNew"]

def GetInvoiceDirUsed():
    return GLOBAL_cfg["invoiceDirUsed"]

def GetCkTag():
    return GLOBAL_cfg["checkingTag"]

def GetCcTag():
    return GLOBAL_cfg["creditCardTag"]

def GetCcAcct():
    return GLOBAL_cfg["creditCardAcct"]

def GetCkCsvSortColumn():
    return GLOBAL_cfg["checkingCsvSortColumn"]

def GetCcCsvSortColumn():
    return GLOBAL_cfg["creditCardCsvSortColumn"]

def GetCkCsvSkip():
    return GLOBAL_cfg["checkingCsvSkip"]

def GetCcCsvSkip():
    return GLOBAL_cfg["creditCardCsvSkip"]
