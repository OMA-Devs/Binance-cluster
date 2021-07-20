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

workerTypes = ["dbWorker", "dbMiner"]

db = DB()

def test_general():
	print("|TESTING CONTAINER ENVIRONMENT")
	a = ""
	for wT in workerTypes:
		if wT == "dbWorker":
			a = dbWorker(argv[1], wT)
			print(f"--->WorkerType: {a.work}")
			if len(a.API) > 0:
				print(f"--->APIKEYS: OK")
			else:
				print(f"--->APIKEYS: KO")
	print("|Conexion con API de BINANCE")
	kline = a.client.get_historical_klines("BTCEUR", a.client.KLINE_INTERVAL_1DAY, "1 week ago")
	print(f"--->Klines en la peticion (7): {len(kline)}")
	print("|Conexion con DB")
	b = db.getSymbols()
	print(f"--->Pares en DB local: {len(b)}")

class Worker:
	def __init__(self, user, workType):
		self.API = db.getAPI(user)
		self.work = workType
		self.client = Client(self.API[0], self.API[1])

class dbWorker(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
		self.updateTime = timedelta(hours=2)
		#self.updateTime = {"hour": 2, "minute": 0}
	def startWork(self, instaTrigger = False):
		last = datetime.now()
		if instaTrigger == False:
			db.updateSymbols(self.client)
			print(f"Next Check at: {last+self.updateTime}")
			while True:
				now = datetime.now()
				if now >= last + self.updateTime:
					db.updateSymbols(self.client)
					last = now
		elif instaTrigger == True:
			db.updateSymbols(self.client)

class dbMiner(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
		self.servType = "servData"
	def startWork(self):
		pairs = db.servePairs(self.servType)
		for pair in pairs:
			print(f'Checking {pair["symbol"]} in db')
			db._checkData(pair["symbol"])

		
if __name__ == "__main__":
	#test_general()
	##argv1 = USER
	##argv2 = workerType
	if argv[2] in workerTypes:
		if argv[2] == "dbWorker":
			worker = dbWorker(argv[1], argv[2])
		if argv[2] == "dbMiner":
			worker = dbMiner(argv[1], argv[2])
		try:
			worker.startWork()
		except KeyboardInterrupt:
			print(f"Proceso terminado manualmente.")
	else:
		print("WorkerType No Definido")