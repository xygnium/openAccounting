# openAccounting
1. learn SQL, mariadb, Python, AWS, double entry accounting, ML/AI, web apps
2. reduce time spent on, increase accuracy and confidence in bookkeeping and tax return preparation
3. cost and feature control
4. anywhere access
5. improved security, backup, and disaster recovery
# How it works
Financial events are input from csv files downloaded from a bank or by using commands in the program.  These events are entered into the stage table. Entries progress through a series of statuses (new, review, ready, done, delete). Stage entries are assigned the "new" status when first entered. Duplicated or unwanted stage entries are identified and assigned a "deleted" status. Stage entries have information added to them, like a description, an invoice file name, and an account id.  The entries then move to the "review" status where they can be corrected if needed, and assigned the "ready" status. Entries with a "ready" status can be committed as two entries into the transactions table. After they are committed, the stage entries are assigned the "done" status. 

Financial reports are run using the transactions table.
# Installation
1. install mariadb
2. install Python 3 (if needed)
3. clone this project
# Setup
1. create database
2. create tables
3. create configuration file
# Start
`<path to clone dir>/oa.py   <path to cfg file>/cfgfile`

Use the *h* command to see a list of commands.
# Build account table
Use the *addac* command.
# Initial stage and transactions tables
These tables are empty initially
