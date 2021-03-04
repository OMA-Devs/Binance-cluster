#!/usr/bin/env python3

import sqlite3
from binance.client import Client
from datetime import datetime
from decimal import Decimal

class DB:
	"""Clase que engloba todas las operaciones de base de datos. Se ha hecho necesaria ya que la modularización del programa está causando
	que haya muchas llamadas desperdigadas por las funciones y mucho codigo duplicado (apertura, commit, cierre) en cada una de ellas.
	"""
	def __init__(self, name, client, shift):
		"""Inicializacion de la clase. Sencilla, simplificada. Solo requiere un nombre de base de datos y una instancia de cliente
		de BINANCE para funcionar.

		Args:
			name (String): Nombre de la base de datos. Existe el argumento debido a que pueden utilizarse dos bases de datos. La de prueba
			y la de produccion. Las API de binance de prueba y produccion son diferentes.
			client (binance.Client): Instancia de cliente de binance, utilizado para obtener informacion del exchange y poco más.
			shift (str|bool): Para especificar en la conexion el campo shift de los trades o "ALL" para las busquedas generales.  
		"""
		self.name = name
		self.testName = "/var/www/html/Binance/master/tests.db"
		self.client = client
		self.shift = str(shift)
	def updateSymbols(self):
		"""Borra y reescribe completamente la tabla de simbolos en la base de datos
		"""
		old = self.getSymbols() #Lista actual de simbolos
		diff = [] #Lista diferencial de simbolos
		db = sqlite3.connect(self.name)
		cur = db.cursor()
		#Borra toda la tabla
		cur.execute("DELETE FROM symbols")
		db.commit()
		#Obtiene todos los simbolos del exchange e itera sobre ellos.
		for sym in self.client.get_exchange_info()["symbols"]:
			minNotional = "-"
			minQty = "-"
			stepSize = "-"
			precision = "-"
			acierto = "0"
			total = "0"
			percent = "0"
			for filt in sym["filters"]:
				if filt["filterType"] == "MIN_NOTIONAL":
					minNotional = filt["minNotional"]
				elif filt["filterType"] == "LOT_SIZE":
					minQty = filt["minQty"]
					stepSize = filt["stepSize"]
			try:
				precision = sym["baseAssetPrecision"]
			except KeyError:
				pass
			queryARR = ["'"+sym["symbol"]+"'",
						"'"+minNotional+"'",
						"'"+minQty+"'",
						"'"+stepSize+"'",
						"'"+str(precision)+"'",
						"'"+acierto+"'",
						"'"+total+"'",
						"'"+percent+"'"]
			querySTR = ",".join(queryARR)
			cur.execute('INSERT INTO symbols VALUES('+querySTR+')')
			db.commit()
			if sym["symbol"] in old:
				pass
			else:
				diff.append(sym["symbol"])
		db.close()
		print("Symbol Database Fully Updated")
		print("- DIFF: "+str(diff))
	def getSymbols(self):
		"""Obtiene una lista de pares limpia de la base de datos.
		Requiere tratamiento porque la base de datos devuelve tuplas.
		El tratamiento convierte las tuplas en diccionarios de mas facil utilización.

		Returns:
			[List]: Lista con todos los simbolos en formato diccionario y sus
			reglas de trading.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT * FROM symbols")
		symList = cur.fetchall()
		db.close()
		clean = []
		#Itera sobre la lista obtenida de la base de datos y convierte las tuplas de un solo elemento en cadenas.
		for i in symList:
			d = {}
			d["symbol"] = i[0]
			d["minNotional"] = i[1]
			d["minQty"] = i[2]
			d["stepSize"] = i[3]
			d["precision"] = i[4]
			d["acierto"] = i[5]
			d["total"] = i[6]
			d["percent"] = [7]
			clean.append(d)
		return clean
	def getTRADINGdict(self):
		"""Obtiene una lista de diccionarios con la información de la tabla trading.

		Returns:
			List: Lista de diccionarios con la información de cada trade en TRADING
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		if self.shift == "ALL":
			cur.execute(f"SELECT * FROM trading")
		else:
			cur.execute(f"SELECT * FROM trading WHERE shift ='{self.shift}'")
		symList = cur.fetchall()
		db.close()
		monitored = []
		for i in symList:
			d = {"symbol": i[0],
				"evalTS": datetime.fromtimestamp(int(i[1].split(".")[0])),
				"evalPrice": i[2],
				"stop": i[3],
				"limit": i[4],
				"assetQty": i[5],
				"baseQty": i[6],
				"shift": i[7]
				}
			monitored.append(d) 
		return monitored
	def getTRADINGsingle(self, sym):
		"""Funcion rapida para chequear si el simbolo esta en trading activo. Se utiliza en DB.getTRADEABLE

		Args:
			shift (str|bool): Descriptor para devolver trades reales en turno, test
			de recopilacion de datos o todo. True para los reales, False para los test
			y ALL para todos.

		Returns:
			Bool: Dependiendo de si existe o no en la tabla.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT symbol FROM trading WHERE symbol = '"+sym+"' AND shift = '"+self.shift+"'")
		symList = cur.fetchall()
		#print(sym+str(len(symList)))
		db.close()
		if len(symList) > 0:
			return True
		else:
			return False
	def getTRADEABLE(self, baseSym):
		"""Devuelve una lista limpia de los simbolos que no tienen trades abiertos con la moneda base determinada.

		Args:
			baseSym (STR): Moneda base
		"""
		symList = self.getSymbols()
		buyable = []
		for sym in symList:
			Lass = len(baseSym)
			if sym["symbol"][Lass-Lass*2:] == baseSym:
				if self.getTRADINGsingle(sym["symbol"]) == False:
					buyable.append(sym)
		#print(len(buyable))
		return buyable
	def getTRADEDdict(self):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		if self.shift == "ALL":
			cur.execute("SELECT * FROM traded")
		else:
			cur.execute(f"SELECT * FROM traded WHERE shift = '{self.shift}'")
		symList= cur.fetchall()
		db.close()
		traded = []
		for sym in symList:
			d = {"symbol": sym[0],
				"evalPrice": sym[1],
				"stop": sym[2],
				"limit": sym[3],
				"sell": sym[4],
				"assetQty": sym[5],
				"baseQty": sym[6],
				"evalTS": datetime.fromtimestamp(int(sym[7].split(".")[0])),
				"endTS": datetime.fromtimestamp(int(sym[8].split(".")[0])),
				"shift": sym[9]}
			traded.append(d)
		return traded
	def tradeEND(self, sym, endTS, sellP):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT * FROM trading WHERE symbol = '"+sym+"' AND shift = '"+self.shift+"'")
		row = cur.fetchall()
		'''sym, evalPrice, stop, limit, sellP, assetQty, baseQty, evalTS, endTS, shift'''
		values = ["'"+sym+"'",
			"'"+row[0][2]+"'",
			"'"+row[0][3]+"'",
			"'"+row[0][4]+"'",
			"'"+sellP+"'",
			"'"+row[0][5]+"'",
			"'"+row[0][6]+"'",
			"'"+row[0][1]+"'",
			"'"+endTS+"'",
			"'"+row[0][7]+"'"]
		query = ",".join(values)
		cur.execute("DELETE FROM trading WHERE symbol = '"+sym+"' AND shift = '"+self.shift+"'")
		db.commit()
		cur.execute("INSERT INTO traded VALUES("+query+")")
		db.commit()
		db.close()
	def tradeSTART(self, sym, evalTS, evalPrice, stop, limit, assetQty, baseQty):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		values = ["'"+sym+"'",
			"'"+evalTS+"'",
			"'"+evalPrice+"'",
			"'"+stop+"'",
			"'"+limit+"'",
			"'"+assetQty+"'",
			"'"+baseQty+"'",
			"'"+self.shift+"'"]
		query = ",". join(values)
		cur.execute("INSERT INTO trading VALUES("+query+")")
		db.commit()
		db.close()
	def removeTrade(self, sym):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("DELETE FROM trading WHERE symbol = '"+sym+"' AND shift = '"+self.shift+"'")
		db.commit()
		db.close()
	def getTRADEDhistoric(self):
		db = sqlite3.connect(self.testName, timeout=30)
		cur = db.cursor()
		query = f"SELECT tableName from lookup"
		cur.execute(query)
		tables = cur.fetchall()
		traded = []
		for name in tables:
			query = f"SELECT * from {name[0]}"
			cur.execute(query)
			symList = cur.fetchall()
			for sym in symList:
				d = {"symbol": sym[0],
					"evalPrice": sym[1],
					"stop": sym[2],
					"limit": sym[3],
					"sell": sym[4],
					"assetQty": sym[5],
					"baseQty": sym[6],
					"evalTS": datetime.fromtimestamp(int(sym[7].split(".")[0])),
					"endTS": datetime.fromtimestamp(int(sym[8].split(".")[0])),
					"shift": sym[9]}
				traded.append(d)
		db.close()
		return traded
	def getPercentage(self, asset="ALL"):
		actual = self.getTRADEDdict()
		historic = self.getTRADEDhistoric()
		full = actual+historic

		hourRange = []
		STAgoodBar = [] #Lista de ganadores
		STAbadBar = [] #Lista de perdedores
		STApercBar = [] #Lista de porcentajes
		STAtots = [] #Lista de trades totales
		for i in range(24):
			hourRange.append(f"{i}")
			STAgoodBar.append(0)
			STAbadBar.append(0)
			STApercBar.append(0)
			STAtots.append(0)
		Lass = len(asset)
		for item in full:
			if asset == "ALL" or item["symbol"][Lass-Lass*2:] == asset:
				evalPrice = Decimal(item["evalPrice"])
				endPrice = Decimal(item["sell"])
				if endPrice > evalPrice:
					item["tradeEND"] = True
				else:
					item["tradeEND"] = False
				STAhour = item["evalTS"].hour
				if item["tradeEND"] == True:
					STAgoodBar[STAhour] = STAgoodBar[STAhour] + 1
				else:
					STAbadBar[STAhour] = STAbadBar[STAhour] + 1
		for i in range(24):
			try:
				tot = STAgoodBar[i]+STAbadBar[i]
				STAtots[i] = tot
				perc = (STAgoodBar[i]/tot)*100
				STApercBar[i] = perc
			except ZeroDivisionError:
				STApercBar[i] = 0
		'''print(f"-----\n|{asset}|\n-----")
		for i in range(24):
			if STApercBar[i] > 60:
				print(f"{hourRange[i]}: {STApercBar[i]:.3f}| Trades: {STAgoodBar[i]+STAbadBar[i]}")'''
		return {"hour":hourRange, "perc": STApercBar, "totals": STAtots}
	def getBestShift(self,minPerc, asset="ALL"):
		perc = self.getPercentage(asset)
		hours = []
		percs = []
		for i in range(24):
			if perc["perc"][i] >= minPerc:
				hours.append(perc["hour"][i])
				percs.append(perc["perc"][i])
		return {"hour": hours, "perc": percs}

if __name__ == "__main__":
	from os import environ
	api_key = environ.get("TEST_BINANCE_API")
	api_sec = environ.get("TEST_BINANCE_SEC")
	real_api_key = environ.get("BINANCE_API_KEY")
	real_api_sec = environ.get("BINANCE_API_SEC")
	client = Client(real_api_key,real_api_sec)
	db = DB("../binance.db", client, "ALL")
	#db.updateSymbols()
	for i in ["ALL","BTC","ETH","BNB"]:
		print(i)
		shift = db.getBestShift(60,asset=i)
		for ind,h in enumerate(shift["hour"]):
			print(f"{h}: {shift['perc'][ind]:.2f}")

