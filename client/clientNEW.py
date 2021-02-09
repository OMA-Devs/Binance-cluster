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
import multiprocessing

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
debug = True

tradepool = []

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
			now = datetime.now()
			if now >= tnow+tick:
				tnow = now+tick
				try:
					act = Decimal(client.get_symbol_ticker(symbol=symbol)["price"])
					#print(f"{symbol}: {act}")
					if act >= limit or act <= stop:
						if debug == False:
							client.order_market_sell(symbol=symbol, quantity=qty)
							print(symbol+ "- Trade cerrado en: "+f"{act:.8f}")
							putTraded(symbol, f"{act:.8f}")
							break
						else:
							print(symbol+ "- Trade cerrado en: "+f"{act:.8f}")
							putTraded(symbol, f"{act:.8f}")
							break
				except (requests.exceptions.ConnectionError,
						requests.exceptions.ConnectTimeout,
						requests.exceptions.HTTPError,
						requests.exceptions.ReadTimeout,
						requests.exceptions.RetryError):
					print("Error en peticion, continuando.")
	except KeyboardInterrupt:
		if debug == False:
			client.order_market_sell(symbol=symbol, quantity=qty)
			putTraded(symbol, f"{act:.8f}")
		else:
			print("Trade cerrado manualmente")
			putTraded(symbol, f"{act:.8f}")

class Checker:
	def __init__(self, at):
		self.at = at
	def stage1(self):
		weight = 0
		#max weight 30
		for ind, val in enumerate(self.at.min5grow):
			if val >= 0.4:
				weight = weight + ((ind+1)*2)
			elif val >= 0 and val < 0.4:
				pass
			elif val < 0:
				weight = weight - ((ind+1)*2)
		if weight > 18:
			print(self.at.pair+"-STAGE 1- Cualifica")
			#print("---"+ str(self.at.min5grow))
			return True
		else:
			#print(self.at.pair+": NO Cualifica PESO: "+str(weight))
			#print("---"+ str(self.at.min5grow))
			return False
	def stage2(self):
		limitPrice = (self.at.qtys["evalPrice"]/100)*self.at.limitPrice
		if limitPrice < self.at.maxDay:
			marginAVG = (self.at.medDay/100)*self.at.limitPrice
			if self.at.qtys["evalPrice"] <= marginAVG:
				print(self.at.pair+"- STAGE 2- Cualifica")
				return True
			else:
				print(f"{self.at.pair} - STAGE 2 NO Cualifica. Precio actual superior a media+limit: {marginAVG:{self.at.data['precision']}}")
				return False
		else:
			print(self.at.pair+"- STAGE 2- NO Cualifica. Limit por encima del maximo diario: "+f"{limitPrice:{self.at.data['precision']}}")
			return False




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
	def _getGrow(self, kline):
		"""Calcula el porcentaje de crecimiento de cada vela de un kline dado

		Args:
			kline ([type]): [description]

		Returns:
			[type]: [description]
		"""
		growARR = []
		for line in kline:
			op = Decimal(line[1])
			cl = Decimal(line[4])
			perc = round((cl-op)/op*100,3)
			growARR.append(perc)
		return growARR
	def _getMinMax(self, kline):
		"""Obtiene el cierre mas alto y el mas bajo, ignorando maximos y minimos para evitar pumps and dumps
		ANTES-Obtiene el HIGH y LOW de un Kline dado

		Args:
			kline (LIST): Kline en formato Binance

		Returns:
			LIST: Lista que contiene "LOW/HIGH" del Kline completo.
		"""
		maximum = 0
		minimum = 99999
		#Determinamos el minimo y el maximo de un kline dado mirando cierres.
		for line in kline:
			cl = Decimal(line[4])
			##Maximo
			if cl > maximum:
				maximum = cl
			#Minimo
			if cl < minimum:
				minimum = cl
		return [minimum,maximum]
	def _getMedium(self,kline):
		"""Calcula la media de precio de un Kline cogiendo el cierre de cada vela.

		Args:
			kline (LIST): Kline argumento

		Returns:
			[Decimal]: Precio medio calculado
		"""
		nums = []
		med = 0
		for line in kline:
			nums.append(Decimal(line[4]))
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
						"qty: "+f"{startQty:{self.data['precision']}}",
						"-"*30]
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
						[f"",
							f"",
							f""],
						[f"{self.qtys['evalPrice']:{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*self.stopPrice):{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*self.limitPrice):{self.data['precision']}}"])
		else:
			msg.append("Orden de compra no ejecutada. No hay suficiente cantidad de "+config.symbol)
			logger(self.logName,msg)
	def startingAnalisys(self):
		"""[summary]
		"""
		check = Checker(self)
		stage1 = check.stage1()
		if stage1 == True or self.force == True:
			self.dayKline = self.client.get_historical_klines(self.pair, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
			self.setDay()
			act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
			self.qtys["evalPrice"] = act
			stage2 = check.stage2()
			if stage2 == True or self.force == True:
				self.checkRules()
				self.openTrade()
				self.monitor = True
				mesARR = ["-"*60,
					self.pair+" MONITOR",
					str(datetime.now()),
					"DAY min/med/max: "+ f"{self.minDay:{self.data['precision']}}"+" / "+f"{self.medDay:{self.data['precision']}}"+" / "+f"{self.maxDay:{self.data['precision']}}",
					"Day grow: "+ str(self.growDay)+"%",
					"Entrada:"+f"{act:{self.data['precision']}}",
					"Limit: "+f"{((act/100)*self.limitPrice):{self.data['precision']}}",
					"Stop: "+f"{((act/100)*self.stopPrice):{self.data['precision']}}"]
				for line in self.min5grow:
					mesARR.append("--: "+str(line)+"%")
				logger(self.logName, mesARR)
	def __init__(self, client, pair, min5Kline, force=False):
		self.client = client
		self.data = pair
		self.data["minNotional"] = Decimal(self.data["minNotional"])
		self.data["minQty"] = Decimal(self.data["minQty"])
		self.data["stepSize"] = Decimal(self.data["stepSize"])
		self.data["precision"] = "."+self.data["precision"]+"f"
		self.pair = self.data["symbol"]
		self.min5Kline = min5Kline #kline de los ultimos 5 minutos, minuto a minuto.
		self.min5grow = self._getGrow(min5Kline)
		self.dayKline = None
		self.minDay = 0 #Precio minimo del dia
		self.maxDay = 0 #Precio maximo del dia
		self.medDay = 0 #Precio medio del dia
		#self.min1h = 0 #Precio minimo 1h
		#self.max1h = 0 #Precio maximo 1h
		#self.med1h = 0 #Precio medio 1h
		self.growDay = 0 #Crecimiento (en porcentaje) del día
		#self.grow1hTOT = self._getPercentage(self.dayKline[-60:]) #Crecimiento (en porcentaje) de una hora en total
		#self.grow1h = [] #Crecimiento (en porcentaje) de la ultima hora, minuto a minuto.
		#self.monitorPERC = 1 #Porcentaje en el que si inician las operaciones y el monitoreo
		self.maxINV = 20 #Inversion maxima en EUR. Se considerara cantidad minima segun las reglas de trading.
		self.force = force
		self.monitor = False
		self.logName = self.pair+"-"+str(datetime.now().date())
		self.limitPrice = 105 # Porcentaje maximo para salir de la posicion.
		self.stopPrice = 95 # Porcentaje minimo para vender.
		#self.setHour()
		#self.setDay()
		self.qtys = {"baseQty":"",
					"eurQty": "",
					"assetQty":"",
					"evalPrice": ""}
		#self.setLimits()
		self.startingAnalisys()
		if self.monitor == True:
			mon = multiprocessing.Process(target=monitor,
										args=(self.pair,str(self.limitPrice),str(self.stopPrice),str(self.qtys["baseQty"]),),
										name= self.pair)
			mon.daemon = True
			tradepool.append(mon)
			mon.start()


if __name__ == "__main__":
	while True:
		try:
			tradeable = getTradeable()
			for ind, j in enumerate(tradepool):
				if j.is_alive() == False:
					tradepool.pop(ind)
			print("Comenzando comprobacion "+config.symbol+": "+str(datetime.now()))
			if len(tradepool) > 0:
				print("Trades Abiertos:")
				for j in tradepool:
					print("- "+ j.name)
			for sym in tradeable:
				#print(sym)
				kline = client.get_historical_klines(sym["symbol"], Client.KLINE_INTERVAL_1MINUTE, "5 minutes ago UTC")
				if len(kline) > 0:
					a = AT(client, sym, kline)
		except (requests.exceptions.ConnectionError,
				requests.exceptions.ConnectTimeout,
				requests.exceptions.HTTPError,
				requests.exceptions.ReadTimeout,
				requests.exceptions.RetryError):
			print("Error, saltando a siguiente comprobacion")