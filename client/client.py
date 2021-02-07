#!/usr/bin/env python3

import requests
from os import environ, system
from sys import argv
import config
from binance.client import Client
from binance.enums import SIDE_SELL, TIME_IN_FORCE_GTC
from datetime import datetime, timedelta
from decimal import Decimal
from ast import literal_eval

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
debug = True

def logger(logName, mesARR):
	f = open("logs/"+logName+".log", "a+")
	for line in mesARR:
		f.write(line+"\n")
		print(line)
	f.close()

def getTradeable():
	payload= {"sym": config.symbol}
	r = requests.get('http://'+config.masterIP+'/data/getTradeable?', params=payload)
	text = r.text
	try:
		final = literal_eval(text)
		return final
	except SyntaxError:
		print("Sin respuesta de masterNode. Solicitando de nuevo.")
		return []

def putTrading(sym, dayStats, hourStats, prices):
	daySTR = "|".join(dayStats)
	hourSTR = "|".join(hourStats)
	ts = str(datetime.timestamp(datetime.now()))
	payload = {"sym": sym,
				"evalTS": ts,
				"dayMAM": daySTR,
				"hourMAM": hourSTR,
				"evalPrice": prices[0],
				"stop": prices[1],
				"limit": prices[2]}
	r = requests.get("http://"+config.masterIP+"/data/putTrading?",params= payload)
	response = r.text
	if literal_eval(response) == True:
		print("Trade enviado a masterNode")
	else:
		print("Trade no recibido en masterNode")

def putTraded(sym, closePrice):
	ts = str(datetime.timestamp(datetime.now()))
	payload = {"sym": sym,
				"endTS": ts,
				"sellPrice": closePrice
				}
	r = requests.get("http://"+config.masterIP+"/data/putTraded?",params= payload)
	response = r.text
	if literal_eval(response) == True:
		print("Trade enviado a masterNode")
	else:
		print("Trade no recibido en masterNode")

def monitor(symbol, limit, stop, qty):
	tick = timedelta(seconds=2)
	limit = Decimal(limit)
	stop = Decimal(stop)
	tnow = datetime.now()
	try:
		while True:
			if datetime.now() >= tnow+tick:
				tnow = datetime.now()+tick
				try:
					act = Decimal(client.get_symbol_ticker(symbol=symbol))
					if act >= limit or act <= stop:
						if debug == False:
							client.order_market_sell(symbol=symbol, quantity=qty)
							putTraded(symbol, f"{act:.8f}")
							break
						else:
							print("Trade cerrado")
							putTraded(symbol, f"{act:.8f}")
				except (requests.exceptions.ConnectionError,
						requests.exceptions.ConnectTimeout,
						requests.exceptions.HTTPError,
						requests.exceptions.ReadTimeout,
						requests.exceptions.RetryError):
					print("Error, continuando con la peticion.")
	except KeyboardInterrupt:
		if debug == False:
			client.order_market_sell(symbol=symbol, quantity=qty)
			putTraded(symbol, f"{act:.8f}")
		else:
			print("Trade cerrado manualmente")
			putTraded(symbol, f"{act:.8f}")
class AT:
	"""Clase de analisis tecnico. Ejecuta la clasificacion de los datos y luego el algoritmo de cualificacion
	y, si cumplen los parametros, ejecuta la funcion Trader en un proceso externo.
	"""
	def _getPercentage(self, kline):
		"""Obtiene el porcentaje TOTAL de un Kline dado

		Args:
			kline (LIST): Lista en formato Kline Binance

		Returns:
			INT: Porcentaje calculado
		"""
		op = Decimal(kline[0][1])
		cl = Decimal(kline[-1][4])
		perc = round((cl-op)/op*100,3)
		return perc
	def _getGrow(self):
		"""Obtiene el crecimiento de cada vela de un Kline. Esta configurado para calcular solo las de la ultima
		hora

		Returns:
			[LIST]: Lista de porcentajes.
		"""
		##Obtiene el crecimiento de cada line en el Kline de 1 hora.
		growARR = []
		for line in self.dayKline[-60:]:
			op = Decimal(line[1])
			cl = Decimal(line[4])
			perc = round((cl-op)/op*100,3)
			growARR.append(perc)
		return growARR
	def _getMinMax(self, kline):
		"""Obtiene el HIGH y LOW de un Kline dado

		Args:
			kline (LIST): Kline en formato Binance

		Returns:
			LIST: Lista que contiene "LOW/HIGH" del Kline completo.
		"""
		maximum = 0
		minimum = 99999
		#Determinamos el minimo y el maximo de un kline dado mirando aperturas y cierres.
		for line in kline:
			##Maximo
			if Decimal(line[2]) > maximum:
				maximum = Decimal(line[2])
			#Minimo
			if Decimal(line[3]) < minimum:
				minimum = Decimal(line[3])
		return [minimum,maximum]
	def _getMedium(self,kline):
		"""Calcula la media de precio de un Kline

		Args:
			kline (LIST): Kline argumento

		Returns:
			[Decimal]: Precio medio calculado
		"""
		nums = []
		med = 0
		for line in kline:
			minimum = Decimal(line[3])
			maximum = Decimal(line[4])
			num = (minimum+maximum)/2
			nums.append(num)
		for num in nums:
			med = med + num
		med = med/len(nums)
		return med
	def setDay(self):
		"""Calcula las estadisticas referentes al día
		"""
		MinMax = self._getMinMax(self.dayKline)
		self.minDay = MinMax[0]
		self.maxDay = MinMax[1]
		self.medDay = self._getMedium(self.dayKline)
		self.growDay = self._getPercentage(self.dayKline)
	def setHour(self):
		"""Calcula las estadisticas referentes a la ultima hora.
		"""
		MinMax = self._getMinMax(self.dayKline[-60:])
		self.min1h = MinMax[0]
		self.max1h = MinMax[1]
		self.med1h = self._getMedium(self.dayKline[-60:])
		self.grow1h = self._getGrow()
	def setLimits(self):
		"""FUNCION ACTUALMENTE EN DESUSO
		"""
		"""act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
		for i in range(105,111):
		#Comprueba si puede generar un beneficio superior al 5%
			if (act/100)*i < self.maxDay and act <= (self.medDay/100)*105:
				self.limitPrice = i
		#if self.limitPrice == 0:
		#	self.limitPrice = 105
		########################################################
		'''for i in range(92, 96):
		#Comprueba si puede marcar un stop menor al 8%
			if (act/100)*i > self.min1h:
				self.stopPrice = i'''
		if self.stopPrice == 0:
			self.stopPrice = 95"""
		pass
	def checkRules(self):
		act = Decimal(client.get_symbol_ticker(symbol=self.pair)["price"])
		startQty = Decimal("0")
		while True:
			startQty = startQty+self.data["stepSize"]
			notionalVALUE = startQty*act
			if notionalVALUE >= self.data["minNotional"] and startQty >= self.data["minQty"]: ##Se cumple el check minNOTIONAL
				eurP = Decimal(client.get_symbol_ticker(symbol=config.symbol+"EUR")["price"])
				qtyEUR = notionalVALUE*eurP
				if startQty>self.data["minQty"] and (startQty-self.data["minQty"])%self.data["stepSize"] == 0 and qtyEUR >= self.maxINV:
					self.qtys["baseQty"] = f"{startQty:{self.data['precision']}}"
					self.qtys["eurQty"] = f"{qtyEUR:{self.data['precision']}}"
					self.qtys["assetQty"] = f"{notionalVALUE:{self.data['precision']}}"
					msg = [f"Trading Rules Check PASSED",
						"Price:"+f"{act:{self.data['precision']}}",
						"EUR TO TRADE: "+f"{qtyEUR:{self.data['precision']}}",
						config.symbol+" TO TRADE: "+f"{notionalVALUE:{self.data['precision']}}",
						"qty: "+f"{startQty:{self.data['precision']}}"]
					logger(self.logName, msg)
					break
				else:
					pass
	def openTrade(self):
		msg = []
		bal = self.client.get_asset_balance(config.symbol)
		if Decimal(bal['free']) > Decimal(self.qtys["assetQty"]):
			msg.append("Ejecutando Orden de compra")
			if debug == False:
				self.client.order_market_buy(symbol=self.pair, quantity=self.qtys["baseQty"])
			else:
				pass
			msg.append("Orden de compra ejecutada")
			logger(self.logName, msg)
			putTrading(self.pair,
						[f"{self.minDay:{self.data['precision']}}",
							f"{self.medDay:{self.data['precision']}}",
							f"{self.maxDay:{self.data['precision']}}"],
						[f"{self.min1h:{self.data['precision']}}",
							f"{self.med1h:{self.data['precision']}}",
							f"{self.max1h:{self.data['precision']}}"],
						[f"{self.qtys['evalPrice']:{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*self.stopPrice):{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*self.limitPrice):{self.data['precision']}}"])
		else:
			msg.append("Orden de compra no ejecutada. No hay suficiente cantidad de "+config.symbol)
			logger(self.logName,msg)
	def startingAnalisys(self):
		"""[summary]
		"""
		#######STAGE 1################
		weight = 0
		if self.grow1hTOT >= self.monitorPERC:
			min3 = self.grow1h[-3:]
			for ind, val in enumerate(min3):
				try:
					if val >= 0.4 and val < min3[ind+1]:
						weight = weight + ((ind+1)*2)
					else:
						weight = weight - ((ind+1)*2)
				except IndexError:
					if val >= 0.4:
						weight = weight + ((ind+1)*2)
					else:
						weight = weight - ((ind+1)*2)
			if weight > 6:
				print(self.pair+"-STAGE 1- Cualifica")
				self.monitor = True
			else:
				#print(self.at.pair+": NO Cualifica PESO: "+str(weight))
				#print("---"+ str(min3))
				self.monitor = False
		else:
			#print(self.at.pair+": NO Cualifica CREC: "+ str(self.at.grow1hTOT)+"%")
			self.monitor = False
		############################################################################
		###################STAGE 2#################################################
		if self.monitor == True or self.force == True:
			act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
			if ((act/100)*self.limitPrice < self.maxDay and act <= (self.medDay/100)*self.limitPrice) or self.force == True:
				print(self.pair+"- STAGE 2- Cualifica")
				self.logName = self.pair+"-"+str(datetime.now().date())
				self.qtys["evalPrice"] = act
				self.checkRules()
				self.openTrade()
				mesARR = ["-"*60,
					self.pair+" MONITOR",
					str(datetime.now()),
					"DAY min/med/max: "+ f"{self.minDay:{self.data['precision']}}"+" / "+f"{self.medDay:{self.data['precision']}}"+" / "+f"{self.maxDay:{self.data['precision']}}",
					"HOUR min/med/max: "+ f"{self.min1h:{self.data['precision']}}"+" / "+f"{self.med1h:{self.data['precision']}}"+" / "+f"{self.max1h:{self.data['precision']}}",
					"Day/1h grow: "+ str(self.growDay)+"% / "+str(self.grow1hTOT)+"%",
					"Entrada:"+f"{act:{self.data['precision']}}",
					"Limit: "+f"{((act/100)*self.limitPrice):{self.data['precision']}}",
					"Stop: "+f"{((act/100)*self.stopPrice):{self.data['precision']}}"]
				for line in self.grow1h[-3:]:
					mesARR.append("--: "+str(line)+"%")
				logger(self.logName, mesARR)
			else:
				self.monitor = False
				print(self.pair+"- STAGE 2- NO Cualifica")
	def __init__(self, client, pair, dayKline, force=False):
		"""[summary]

		Args:
			client (binance.client.Client): instancia de cliente
			pair (DICT): Diccionario con el simbolo y reglas de trading relacionadas.
			dayKline(LIST): Kline de 24h minuto a minuto.
		"""
		#print("NOT IN TRADING")
		self.client = client
		self.data = pair
		self.data["minNotional"] = Decimal(self.data["minNotional"])
		self.data["minQty"] = Decimal(self.data["minQty"])
		self.data["stepSize"] = Decimal(self.data["stepSize"])
		self.data["precision"] = "."+self.data["precision"]+"f"
		self.pair = self.data["symbol"]
		self.dayKline = dayKline #kline de la ultima hora, minuto a minuto.
		self.minDay = 0 #Precio minimo del dia
		self.maxDay = 0 #Precio maximo del dia
		self.medDay = 0 #Precio medio del dia
		self.min1h = 0 #Precio minimo 1h
		self.max1h = 0 #Precio maximo 1h
		self.med1h = 0 #Precio medio 1h
		self.growDay = 0 #Crecimiento (en porcentaje) del día
		self.grow1hTOT = self._getPercentage(self.dayKline[-60:]) #Crecimiento (en porcentaje) de una hora en total
		self.grow1h = [] #Crecimiento (en porcentaje) de la ultima hora, minuto a minuto.
		self.monitorPERC = 1 #Porcentaje en el que si inician las operaciones y el monitoreo
		self.maxINV = 20 #Inversion maxima en EUR. Se considerara cantidad minima segun las reglas de trading.
		self.force = force
		self.monitor = False
		self.limitPrice = 105 # Porcentaje maximo para salir de la posicion.
		self.stopPrice = 95 # Porcentaje minimo para vender.
		self.setHour()
		self.setDay()
		self.logName = ""
		self.qtys = {"baseQty":"",
					"eurQty": "",
					"assetQty":"",
					"evalPrice": ""}
		#self.setLimits()
		self.startingAnalisys()
		if self.monitor == True:
			launch = "x-terminal-emulator -e python3 "+argv[0]+" monitor "+self.pair+" "+str(self.limitPrice)+" "+str(self.stopPrice)+" "+str(self.qtys["baseQty"])
			system(launch)


if __name__ == "__main__":
	try:
		if argv[1] == "monitor":
			monitor(argv[2],argv[3],argv[4],argv[5])
	except IndexError:
		while True:
			try:
				tradeable = getTradeable()
				print("Comenzando comprobacion "+config.symbol+": "+str(datetime.now()))
				for sym in tradeable:
					#print(sym)
					kline = client.get_historical_klines(sym["symbol"], Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
					if len(kline) > 0:
						a = AT(client, sym, kline)
			except (requests.exceptions.ConnectionError,
					requests.exceptions.ConnectTimeout,
					requests.exceptions.HTTPError,
					requests.exceptions.ReadTimeout,
					requests.exceptions.RetryError):
					print("Error, saltando a siguiente comprobacion")