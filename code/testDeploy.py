#!/usr/bin/env python3

from os import environ
from datetime import datetime, timedelta
from decimal import Decimal
from binance.client import Client
import mariadb
import dateparser
from dbOPS import DB1 as DB
from dbOPS import parseKline
from sys import argv

print(argv)
f = open(argv[1])
keysecStr = f.readline()
print(keysecStr)
keysecPair = keysecStr.split("|")
real_api_key = keysecPair[0]
real_api_sec = keysecPair[1]
client = Client(real_api_key,real_api_sec)
user = "binance"
password = "binance"
host = "192.168.1.200"
port = 3306
database = "binance"

if __name__ == "__main__":
	print("TESTING CONTAINER ENVIRONMENT")
	print(keysecPair)
	print("Conexion con API de BINANCE")
	kline = client.get_historical_klines("BTCEUR", client.KLINE_INTERVAL_1DAY, "1 week ago")
	for line in kline:
		print(line)
	print("Conexion con DB")
	db = DB(client)

	