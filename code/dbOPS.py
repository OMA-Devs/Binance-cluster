#!/usr/bin/env python3

import sqlite3
from binance.client import Client
from datetime import datetime
from decimal import Decimal
import mariadb
import dateparser
import socket
from requests import exceptions as Rexceptions
from urllib3 import exceptions as Uexceptions

TRADEABLE_ASSETS = ["BTC", "ETH", "BNB"]

def parseKline(kline):
	newKline = []
	for candle in kline:
		newCandle = {
			"openTime": datetime.fromtimestamp(candle[0]/1000),
			"open": Decimal(candle[1]),
			"high": Decimal(candle[2]),
			"low": Decimal(candle[3]),
			"close": Decimal(candle[4])
		}
		newKline.append(newCandle)
	return newKline

def parseSymbol(symbol):
	d = {}
	d["symbol"] = symbol[0]
	d["minNotional"] = symbol[1]
	d["minQty"] = symbol[2]
	d["stepSize"] = symbol[3]
	d["precision"] = symbol[4]
	d["acierto"] = symbol[5]
	d["total"] = symbol[6]
	d["percent"] = symbol[7]
	d["1S"] = symbol[8]
	d["1M"] = symbol[9]
	d["servido"] = symbol[10]
	return d


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
	def updateSymbols(self): #
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
	def getSymbols(self): #
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
				evalPrice = Decimal(d["evalPrice"])
				endPrice = Decimal(d["sell"])
				if endPrice > evalPrice:
					d["tradeEND"] = True
				else:
					d["tradeEND"] = False
				traded.append(d)
		db.close()
		return traded
	'''def getDetailTRADEDhistoric(self): ##########PRUEBA, SIN USO
		db = sqlite3.connect(self.testName, timeout=30)
		cur = db.cursor()
		query = f"SELECT tableName from lookup"
		cur.execute(query)
		tables = cur.fetchall()
		tablesCURED = []
		for name in tables:
			table = {"Name": name[0]}
			query = f"SELECT * from {name[0]}"
			cur.execute(query)
			symList = cur.fetchall()
			table["trades"] = []
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
	 			table["trades"].append(d)
			tablesCURED.append(table)
		db.close()
		for table in tablesCURED:
			table["Start"] = table["trades"][0]["evalTS"]
			table["End"] = table["trades"][-1]["endTS"]
			table["Duration"] = table["End"]-table["Start"]

		for table in tablesCURED:
			print(f"---{table['Name']}---\nInicio: {table['Start']}\nFinal: {table['End']}\nDuracion: {table['Duration']}\nN.Trades: {len(table['trades'])}")
		return tablesCURED'''
	def getEFperDay(self, asset="ALL"):
		##DEMASIADO LARGA. HAY QUE FACTORIZAR. ES MALA CON GANAS
		db = sqlite3.connect(self.testName, timeout=30)
		cur = db.cursor()
		query = f"SELECT tableName from lookup"
		cur.execute(query)
		tables = cur.fetchall()
		days = {}
		Lass = len(asset)
		for name in tables:
			query = f"SELECT * from {name[0]}"
			cur.execute(query)
			symList = cur.fetchall()
			db.close()
			for sym in symList:
				if asset == "ALL" or sym[0][Lass-Lass*2:] == asset:
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
					monthday = f'{d["evalTS"].month}/{d["evalTS"].day}'
					try:
						days[monthday].append(d)
					except KeyError:
						days[monthday] = [d]
		daysCURED = {}
		for key in days:
			TOT = len(days[key])
			GOOD = 0
			BAD = 0
			for item in days[key]:
				evalPrice = Decimal(item["evalPrice"])
				endPrice = Decimal(item["sell"])
				if endPrice > evalPrice:
					item["tradeEND"] = True
					GOOD = GOOD +1
				else:
					item["tradeEND"] = False
					BAD = BAD +1
			perc = (GOOD/TOT)*100
			daysCURED[key] = {"total": TOT, "good": GOOD, "bad": BAD, "perc": perc}
			percDays = {"day": [], "total": [], "good": [], "bad": [], "perc": [],"grow":[], "co": [],"text": []}
		for key in daysCURED:
			percDays["day"].append(key)
			percDays["total"].append(daysCURED[key]["total"])
			percDays["good"].append(daysCURED[key]["good"])
			percDays["bad"].append(daysCURED[key]["bad"])
			percDays["perc"].append(daysCURED[key]["perc"])
		assetRAWData = self.client.get_historical_klines(asset+"EUR", Client.KLINE_INTERVAL_1DAY, percDays["day"][0])
		assetData = {"day":[], "grow": []}
		for i in assetRAWData:
				fechaDT = datetime.fromtimestamp(int(i[0])/1000)
				fechaSTR = f'{fechaDT.month}/{fechaDT.day}'
				if fechaSTR in percDays["day"]:
					assetData["day"].append(fechaSTR)
					op = Decimal(i[1])
					cl = Decimal(i[4])
					perc = round((cl-op)/op*100,3)
					percDays["grow"].append(perc)
		for i in range(len(percDays["day"])):
			try:
				co = Decimal(percDays["grow"][i])/Decimal(percDays["perc"][i]) #COEFICIENTE DE CORRELACION CON EL PRECIO BASE
			except ZeroDivisionError:
				co = Decimal("0.3")
			percDays["co"].append(co)
			percDays["text"].append(f'Efectividad: {percDays["perc"][i]:.3f} || Crecimiento: {percDays["grow"][i]:.3f}|| Total: {percDays["total"][i]:.3f}')

		'''for i in range(len(percDays["day"])):
			#print(percDays["co"][i]== Decimal("0.04"))
			#if Decimal(percDays["co"][i]) <= Decimal("0.030") and Decimal(percDays["co"][i]) >= Decimal("-0.030"):
			print(f'DB: {percDays["day"][i]}||GROW: {percDays["grow"][i]}||EF: {percDays["perc"][i]:.3f}||CO: {percDays["co"][i]:.3f}')'''
		return percDays
	def getMostProficent(self, asset="ALL"):
		historic = db.getTRADEDhistoric()
		actual = db.getTRADEDdict()
		full = historic+actual
		pairDict = {}
		for item in full:
			try:
				pairDict[item["symbol"]]
			except KeyError:
				pairDict[item["symbol"]]= {}
			if item["tradeEND"] == True:
				pairDict[item["symbol"]]["good"] = 1
				pairDict[item["symbol"]]["bad"] = 0
			else:
				pairDict[item["symbol"]]["good"] = 0
				pairDict[item["symbol"]]["bad"] = 1
			if item["tradeEND"] == True:
				pairDict[item["symbol"]]["good"] = pairDict[item["symbol"]]["good"] + 1
			else:
				pairDict[item["symbol"]]["bad"] = pairDict[item["symbol"]]["bad"] + 1
		for pair in pairDict:
			pairOb = pairDict[pair]
			pairOb["total"] = pairOb["good"]+pairOb["bad"] 
			pairOb["efec"] = (pairOb["good"]/pairOb["total"])*100
			print(pairOb)
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


class DB1:
	def __init__(self, client):
		self.user = f"binance"
		self.password = "binance"
		self.host = "192.168.1.54"
		self.port = 3306
		self.database = "binance"
		self.client = client
	def getSymbols(self):
		"""Obtiene una lista de pares limpia de la base de datos.
		Requiere tratamiento porque la base de datos devuelve tuplas.
		El tratamiento convierte las tuplas en diccionarios de mas facil utilización.

		Returns:
			[List]: Lista con todos los simbolos en formato diccionario y sus
			reglas de trading.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		cur.execute("SELECT * FROM symbols")
		clean = []
		#Itera sobre la lista obtenida de la base de datos y convierte las tuplas de un solo elemento en cadenas.
		for i in cur:
			d = parseSymbol(i)
			clean.append(d)
		conn.close()
		return clean
	def updateSymbols(self):
		symDict = self.getSymbols()
		exchDict = self.client.get_exchange_info()["symbols"]
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		#######DELISTED LOOP######
		delisted = []
		for sym in symDict:
			inList = False
			for ex in exchDict:
				if sym["symbol"] == ex["symbol"]:
					inList = True
			if inList == False:
				delisted.append(sym["symbol"])
				st = f"DELETE FROM symbols WHERE symbol='{sym['symbol']}'"
				cur.execute(st)
		#############################
		#######NEWLISTED LOOP########
		newlisted = []
		for sym in exchDict:
			inList = False
			for ex in symDict:
				if ex["symbol"] == sym["symbol"]:
					inList = True
			if inList == False:
				newlisted.append(sym["symbol"])
				minNotional = "-"
				minQty = "-"
				stepSize = "-"
				precision = "-"
				acierto = "0"
				total = "0"
				percent = "0"
				s1 = "0"
				m1 = "0"
				servido = str(datetime.now())
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
							"'"+percent+"'",
							"'"+s1+"'",
							"'"+m1+"'",
							"'"+servido+"'"]
				querySTR = ",".join(queryARR)
				st = f"INSERT INTO symbols VALUES({querySTR})"
				#print(st)
				cur.execute(st)
				conn.commit()
		#############################
		########CROP UTILS###########
		query = f"SELECT * FROM `symbols` WHERE symbol NOT LIKE '%BTC' AND symbol NOT LIKE '%ETH' AND symbol NOT LIKE '%BNB'"
		cur.execute(query)
		toCrop = []
		for pair in cur:
			toCrop.append(pair[0])
		for pair in toCrop:
			query = f"DELETE FROM symbols WHERE symbol = '{pair}'"
			cur.execute(query)
			conn.commit()
		#############################
		#########UPDATE TRENDS#######
		''' Se obtienen las tendencias de 4 periodos en intervalos de 1S y 1M'''
		symDict = self.getSymbols()
		for sym in symDict:
			kline1S = parseKline(client.get_historical_klines(sym['symbol'], Client.KLINE_INTERVAL_1WEEK, "4 weeks ago"))
			if len(kline1S) > 0:
				trend = kline1S[-1]["close"]- kline1S[0]["close"]
				if trend > 0:
					trendString = "BULL"
				else:
					trendString = "BEAR"
				query = f"UPDATE symbols SET 1S = '{trendString}' WHERE symbol = '{sym['symbol']}'"
				cur.execute(query)
				conn.commit()
			kline1M = parseKline(client.get_historical_klines(sym['symbol'], Client.KLINE_INTERVAL_1MONTH, "4 months ago"))
			if len(kline1M) > 0:
				trend = kline1M[-1]["close"]- kline1M[0]["close"]
				if trend > 0:
					trendString = "BULL"
				else:
					trendString = "BEAR"
				query = f"UPDATE symbols SET 1M = '{trendString}' WHERE symbol = '{sym['symbol']}'"
				cur.execute(query)
				conn.commit()
		#############################
		########UPDATE PERCENTS######
		'''symDict = self.getSymbols()
		for sym in symDict:
			trades = self.getPairHistoric("scalper", pair= sym["symbol"])
			if len(trades)>0:
				aciertos = 0
				total = 0
				for trade in trades:
					total = total + 1
					if Decimal(trade["sellPrice"]) > Decimal(trade["evalPrice"]):
						aciertos = aciertos + 1
				perc = (aciertos/total)*100
				st = f"UPDATE symbols SET acierto = '{aciertos}', total = '{total}', percent = '{perc}' WHERE symbol = '{sym['symbol']}' "
				cur.execute(st)
				conn.commit()'''
		#################################
		conn.close()
		st = ""
		for i in delisted:
			st = st+f"{i}\n"
		print("FUERA:")
		print(st)
		st = ""
		print("-"*30)
		for i in newlisted:
			st = st+f"{i}\n"
		print("NUEVOS:")
		print(st)
		print("-"*30)
		print(f"toCrop: {len(toCrop)}")
	'''def tradeSTART(self, sym, evalTS, evalPrice, stop, limit, assetQty, baseQty):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
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
		db.close()'''
	def getPairHistoric(self, cliType,pair = "ALL", start = "FIRST", end = "LAST"):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		st = ""
		startTS = 0
		endTS = 0
		if start == "FIRST":
			startTS = 0
		else:
			startTS = datetime.timestamp(dateparser.parse(start))
		if end == "LAST":
			endTS = 999999999999
		else:
			endTS = datetime.timestamp(dateparser.parse(end))
		if pair == "ALL":
			st = f"SELECT * FROM {cliType}_historic, {cliType}_traded WHERE evalTS > {startTS} AND evalTS < {endTS}"
		else:
			st = f"SELECT * FROM {cliType}_historic, {cliType}_traded WHERE symbol='{pair}' AND evalTS > {startTS} AND evalTS < {endTS}"
		cur.execute(st)
		historic = []
		for trade in cur:
			d = {"_tradeID": trade[0],
				"symbol": trade[1],
				"evalPrice": trade[2],
				"stopPrice": trade[3],
				"limitPrice": trade[4],
				"sellPrice": trade[5],
				"assetQty": trade[6],
				"baseQty": trade[7],
				"evalTS": trade[8],
				"endTS": trade[9],
				"shift": trade[10]}
			historic.append(d)
		conn.close()
		return historic
	def getAssetHistoric(self, cliType, asset = "ALL", start = "FIRST", end = "LAST"):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		st = ""
		startTS = 0
		endTS = 0
		if start == "FIRST":
			startTS = 0
		else:
			startTS = datetime.timestamp(dateparser.parse(start))
		if end == "LAST":
			endTS = 999999999999
		else:
			endTS = datetime.timestamp(dateparser.parse(end))
		if asset == "ALL":
			st = f"SELECT * FROM {cliType}_historic, {cliType}_traded"
		else:
			st = f"SELECT * FROM {cliType}_historic WHERE symbol LIKE '%{asset}' AND evalTS > {startTS} AND evalTS < {endTS}"
		cur.execute(st)
		historic = []
		for trade in cur:
			d = {"_tradeID": trade[0],
				"symbol": trade[1],
				"evalPrice": trade[2],
				"stopPrice": trade[3],
				"limitPrice": trade[4],
				"sellPrice": trade[5],
				"assetQty": trade[6],
				"baseQty": trade[7],
				"evalTS": trade[8],
				"endTS": trade[9],
				"shift": trade[10]}
			historic.append(d)
		conn.close()
		return historic
	def getEFperHour(self, cliType, asset = "ALL", start = "FIRST", end = "LAST"):
		history = self.getAssetHistoric(cliType, asset= asset, start= start, end= end)
		d = {"hour":[], "perc":[], "acierto": [], "total":[]}
		for i in range(24):
			d["hour"].append(f"{i}")
			d["perc"].append(0)
			d["acierto"].append(0)
			d["total"].append(0)
		for trade in history:
			evalPrice = Decimal(trade["evalPrice"])
			endPrice = Decimal(trade["sellPrice"])
			if endPrice > evalPrice:
				trade["tradeEND"] = True
			else:
				trade["tradeEND"] = False
			STAhour = datetime.fromtimestamp(Decimal(trade["evalTS"])).hour
			d["total"][STAhour] = d["total"][STAhour] + 1
			if trade["tradeEND"] == True:
				d["acierto"][STAhour] = d["acierto"][STAhour] + 1
		for i in range(24):
			d["perc"][i] = (Decimal(d["acierto"][i])/Decimal(d["total"][i]))*100
		for key in d:
			print(d[key])
			print("")			
	def serveScalper(self):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		query = f"SELECT * FROM symbols ORDER BY servido ASC LIMIT 50"
		cur.execute(query)
		toServe = []
		for pair in cur:
			toServe.append(parseSymbol(pair))
		for i in toServe:
			#print(i[0])
			query = f"UPDATE symbols SET servido = '{datetime.now()}' WHERE symbol = '{i['symbol']}'"
			cur.execute(query)
			conn.commit()
		conn.close()
		return toServe
	def getHistoricFromAPI(self, pair = "ALL", start = "2 days ago UTC", end = "yesterday UTC"):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		try:
			kline = parseKline(self.client.get_historical_klines(pair, Client.KLINE_INTERVAL_1MINUTE, start_str= start, end_str= end))
		except (Rexceptions.ConnectionError, Uexceptions.ConnectionError,
			Uexceptions.ReadTimeoutError, Rexceptions.ReadTimeout):
			kline = []
			print(f"--> Connection reset, skipping")
		if len(kline) > 0:
			query = f"CREATE TABLE IF NOT EXISTS `{pair}_historic` (`openTime` DATETIME NOT NULL , `open` DECIMAL(40,8) NOT NULL , `high` DECIMAL(40,8) NOT NULL , `low` DECIMAL(40,8) NOT NULL , `close` DECIMAL(40,8) NOT NULL ) ENGINE = InnoDB;"
			cur.execute(query)
			for candle in kline:
				query = f"INSERT INTO {pair}_historic VALUES('{candle['openTime']}', '{candle['open']}', '{candle['high']}', '{candle['low']}', '{candle['close']}')"
				cur.execute(query)
				conn.commit()
		conn.close()

class DB2:
	def __init__(self):
		self.user = f"binance"
		self.password = "binance"
		self.host = "192.168.1.200"
		self.port = 3306
		self.database = "binance"
		#self.client = client
	def getSymbols(self):
		"""Obtiene una lista de pares limpia de la base de datos.
		Requiere tratamiento porque la base de datos devuelve tuplas.
		El tratamiento convierte las tuplas en diccionarios de mas facil utilización.

		Returns:
			[List]: Lista con todos los simbolos en formato diccionario y sus
			reglas de trading.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		cur.execute("SELECT * FROM symbols")
		clean = []
		#Itera sobre la lista obtenida de la base de datos y convierte las tuplas de un solo elemento en cadenas.
		for i in cur:
			d = parseSymbol(i)
			clean.append(d)
		conn.close()
		return clean
	def updateSymbols(self):
		symDict = self.getSymbols()
		exchDict = self.client.get_exchange_info()["symbols"]
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		#######DELISTED LOOP######
		delisted = []
		for sym in symDict:
			inList = False
			for ex in exchDict:
				if sym["symbol"] == ex["symbol"]:
					inList = True
			if inList == False:
				delisted.append(sym["symbol"])
				st = f"DELETE FROM symbols WHERE symbol='{sym['symbol']}'"
				cur.execute(st)
		#############################
		#######NEWLISTED LOOP########
		newlisted = []
		for sym in exchDict:
			inList = False
			for ex in symDict:
				if ex["symbol"] == sym["symbol"]:
					inList = True
			if inList == False:
				newlisted.append(sym["symbol"])
				minNotional = "-"
				minQty = "-"
				stepSize = "-"
				precision = "-"
				acierto = "0"
				total = "0"
				percent = "0"
				s1 = "0"
				m1 = "0"
				servido = str(datetime.now())
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
							"'"+percent+"'",
							"'"+s1+"'",
							"'"+m1+"'",
							"'"+servido+"'"]
				querySTR = ",".join(queryARR)
				st = f"INSERT INTO symbols VALUES({querySTR})"
				#print(st)
				cur.execute(st)
				conn.commit()
		#############################
		########CROP UTILS###########
		query = f"SELECT * FROM `symbols` WHERE symbol NOT LIKE '%BTC' AND symbol NOT LIKE '%ETH' AND symbol NOT LIKE '%BNB'"
		cur.execute(query)
		toCrop = []
		for pair in cur:
			toCrop.append(pair[0])
		for pair in toCrop:
			query = f"DELETE FROM symbols WHERE symbol = '{pair}'"
			cur.execute(query)
			conn.commit()
		#############################
		#########UPDATE TRENDS#######
		''' Se obtienen las tendencias de 4 periodos en intervalos de 1S y 1M'''
		symDict = self.getSymbols()
		for sym in symDict:
			kline1S = parseKline(client.get_historical_klines(sym['symbol'], Client.KLINE_INTERVAL_1WEEK, "4 weeks ago"))
			if len(kline1S) > 0:
				trend = kline1S[-1]["close"]- kline1S[0]["close"]
				if trend > 0:
					trendString = "BULL"
				else:
					trendString = "BEAR"
				query = f"UPDATE symbols SET 1S = '{trendString}' WHERE symbol = '{sym['symbol']}'"
				cur.execute(query)
				conn.commit()
			kline1M = parseKline(client.get_historical_klines(sym['symbol'], Client.KLINE_INTERVAL_1MONTH, "4 months ago"))
			if len(kline1M) > 0:
				trend = kline1M[-1]["close"]- kline1M[0]["close"]
				if trend > 0:
					trendString = "BULL"
				else:
					trendString = "BEAR"
				query = f"UPDATE symbols SET 1M = '{trendString}' WHERE symbol = '{sym['symbol']}'"
				cur.execute(query)
				conn.commit()
		#############################
		########UPDATE PERCENTS######
		'''symDict = self.getSymbols()
		for sym in symDict:
			trades = self.getPairHistoric("scalper", pair= sym["symbol"])
			if len(trades)>0:
				aciertos = 0
				total = 0
				for trade in trades:
					total = total + 1
					if Decimal(trade["sellPrice"]) > Decimal(trade["evalPrice"]):
						aciertos = aciertos + 1
				perc = (aciertos/total)*100
				st = f"UPDATE symbols SET acierto = '{aciertos}', total = '{total}', percent = '{perc}' WHERE symbol = '{sym['symbol']}' "
				cur.execute(st)
				conn.commit()'''
		#################################
		conn.close()
		st = ""
		for i in delisted:
			st = st+f"{i}\n"
		print("FUERA:")
		print(st)
		st = ""
		print("-"*30)
		for i in newlisted:
			st = st+f"{i}\n"
		print("NUEVOS:")
		print(st)
		print("-"*30)
		print(f"toCrop: {len(toCrop)}")
	def getAPI(self, user):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		st = f"SELECT * FROM users WHERE name='{user}'"
		cur.execute(st)
		apiKEYS=[]
		for idAPI in cur:
			apiKEYS.append(idAPI[1])
			apiKEYS.append(idAPI[2])		
		return apiKEYS

if __name__ == "__main__":
	from os import environ
	api_key = environ.get("TEST_BINANCE_API")
	api_sec = environ.get("TEST_BINANCE_SEC")
	real_api_key = environ.get("BINANCE_API_KEY")
	real_api_sec = environ.get("BINANCE_API_SEC")
	client = Client(real_api_key,real_api_sec)
	#db = DB("../binance.db", client, "ALL")
	##db.updateSymbols()
	'''for i in ["ALL","BTC","ETH","BNB"]:
		print(i)
		shift = db.getBestShift(65,asset=i)
		for ind,h in enumerate(shift["hour"]):
			print(f"{h}: {shift['perc'][ind]:.2f}")'''
	#db.getMostProficent()
	#db.getCorrelation(assets="ETH")
	db1 = DB1(client)
	#db1.updateSymbols()
	db1.getHistoricFromAPI(pair="BTCEUR")

