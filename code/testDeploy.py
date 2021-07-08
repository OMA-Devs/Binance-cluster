#!/usr/bin/env python3

from os import environ
from datetime import datetime, timedelta
from decimal import Decimal
from binance.client import Client
import mariadb
import dateparser
from dbOPS import DB2 as DB
from dbOPS import parseKline
from sys import argv

db = DB()

class Worker:
	def __init__(self, user, workType):
		self.API = db.getAPI(user)
		
if __name__ == "__main__":
	print("TESTING CONTAINER ENVIRONMENT")
	a = Worker(argv[1],"scalper")
	print(a.API)
	print("Conexion con API de BINANCE")
	client = Client(a.API[0],a.API[1])
	kline = client.get_historical_klines("BTCEUR", client.KLINE_INTERVAL_1DAY, "1 week ago")
	for line in kline:
		print(line)
	print("Conexion con DB")
