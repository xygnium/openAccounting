#!/usr/bin/env python3

import sys

# local imports

import db
import cfg
import ask
import acct

# --- main ---

print("Open Accounting, v0.1")

cfg.InitCfg()
db.Init()
acct.InitAccounts()

while True:
    if not ask.Cmd():
        sys.exit(0)
