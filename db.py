import sys

def exitPgm(msg, code):
    print(msg)
    sys.exit(code)

def exitAbnormal(conn, msg):
    conn.close()
    exitPgm(msg, -1)

def exitNormal(conn, msg):
    conn.close()
    exitPgm(msg, 0)
