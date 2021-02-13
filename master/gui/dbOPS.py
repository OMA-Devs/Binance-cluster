#!/usr/bin/env python3

import sqlite3
from binance.client import Client
from datetime import datetime

class DB:
	"""Clase que engloba todas las operaciones de base de datos. Se ha hecho necesaria ya que la modularización del programa está causando
	que haya muchas llamadas desperdigadas por las funciones y mucho codigo duplicado (apertura, commit, cierre) en cada una de ellas.
	"""
	def __init__(self, name, client):
		"""Inicializacion de la clase. Sencilla, simplificada. Solo requiere un nombre de base de datos y una instancia de cliente
		de BINANCE para funcionar.

		Args:
			name (String): Nombre de la base de datos. Existe el argumento debido a que pueden utilizarse dos bases de datos. La de prueba
			y la de produccion. Las API de binance de prueba y produccion son diferentes.
			client (binance.Client): Instancia de cliente de binance, utilizado para obtener informacion del exchange y poco más. 
		"""
		self.name = name
		self.client = client
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
			cur.execute('INSERT INTO symbols VALUES("'+sym["symbol"]+'","'+minNotional+'","'+minQty+'","'+stepSize+'","'+str(precision)+'")')
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
			[List]: Lista con todos los simbolos en formato de cadenas de texto y sus
			reglas de trading.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT symbol, minNotional, minQty, stepSize, precision FROM symbols")
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
			clean.append(d)
		return clean
	def getTRADING(self):
		"""Obtiene los simbolos en trading activo.
		Returns:
			List: Lista de simbolos en trading activo.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT symbol FROM trading")
		symList = cur.fetchall()
		db.close()
		monitored = []
		for i in symList:
			monitored.append(i[0])
		return monitored
	def getTRADINGdict(self):
		"""Obtiene los simbolos en trading activo.
		Returns:
			List: Lista de simbolos en trading activo.
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT * FROM trading")
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
				"baseQty": i[6]}
			monitored.append(d) 
		return monitored
	def getTRADINGsingle(self, sym):
		"""Funcion rapida para chequear si el simbolo esta en trading activo. Se utiliza en DB.getTRADEABLE
		"""
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT symbol FROM trading WHERE symbol = '"+sym+"'")
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
	def getTRADED(self):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT * FROM traded")
		symList= cur.fetchall()
		return symList
	def tradeEND(self, sym, endTS, sellP):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("SELECT * FROM trading WHERE symbol = '"+sym+"'")
		row = cur.fetchall()
		'''sym, evalPrice, stop, limit, sellP, assetQty, baseQty, evalTS, endTS'''
		values = ["'"+sym+"'",
			"'"+row[0][2]+"'",
			"'"+row[0][3]+"'",
			"'"+row[0][4]+"'",
			"'"+sellP+"'",
			"'"+row[0][5]+"'",
			"'"+row[0][6]+"'",
			"'"+row[0][1]+"'",
			"'"+endTS+"'"]
		query = ",".join(values)
		cur.execute("DELETE FROM trading WHERE symbol = '"+sym+"'")
		db.commit()
		cur.execute("INSERT INTO traded VALUES("+query+")")
		db.commit()
		db.close()
	def tradeSTART(self, sym, evalTS, evalPrice, stop, limit, assetQty, baseQty):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		values = ["'"+sym+"'",
			"'"+evalTS+"'",
			"'"+stop+"'",
			"'"+limit+"'",
			"'"+assetQty+"'",
			"'"+baseQty+"'"]
		query = ",". join(values)
		cur.execute("INSERT INTO trading VALUES("+query+")")
		db.commit()
		db.close()
	def removeTrade(self, sym):
		db = sqlite3.connect(self.name, timeout=30)
		cur = db.cursor()
		cur.execute("DELETE FROM trading WHERE symbol = '"+sym+"'")
		db.commit()
		db.close()

if __name__ == "__main__":
	from os import environ
	api_key = environ.get("TEST_BINANCE_API")
	api_sec = environ.get("TEST_BINANCE_SEC")
	real_api_key = environ.get("BINANCE_API_KEY")
	real_api_sec = environ.get("BINANCE_API_SEC")
	client = Client(real_api_key,real_api_sec)
	db = DB("../binance.db", client)
	db.updateSymbols()
	#db.tradeEND("EOSBNB", str(datetime.now()),"0.0000")
