# Module Imports
import mariadb
import sys

# Connect to MariaDB Platform
try:
    conn = mariadb.connect(
        user="binance",
        password="admin",
        host="localhost",
        port=3306,
        database="binance"

    )
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

# Get Cursor
cur = conn.cursor()
cur.execute("SELECT symbol FROM symbols")
for sym in cur:
	print(sym)
cur.execute("SELECT minNotional FROM symbols")
for sym in cur:
	print(sym)
