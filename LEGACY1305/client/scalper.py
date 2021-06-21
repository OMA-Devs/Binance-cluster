#!/usr/bin/env python3

#Archivos del programa
import scalperConf
import masterRequests
import checker

#Librerías estandar
import multiprocessing
from datetime import datetime, timedelta
from decimal import Decimal

#Gestión de errores
from requests import exceptions
from OpenSSL import SSL

title = '''
____ ____ ____ _    ___  ____ ____ 
[__  |    |__| |    |__] |___ |__/ 
___] |___ |  | |___ |    |___ |  \\
'''


tradepool = []

def cleanPools():
	for ind,j in enumerate(tradepool):
		if j.is_alive() == False:
			tradepool.pop(ind)

def monitor(symbol, limit, stop, qty):
	"""Función de monitoreo que se ejecuta paralelamente al ciclo principal. Monitorea el precio
	actual respecto a limite y stop, generando una orden de venta inmediatamente si sobrepasa
	uno de los dos. 

	Args:
		symbol (STR): Par del trade
		limit (Decimal): Precio limite.
		stop (Decimal): Precio limite.
		qty (STR): Cantidad de la moneda en trading.
	"""
	tick = timedelta(seconds=2)
	tnow = datetime.now()
	tradeShift = scalperConf.shift ######ESTO PODRIA SER UN PROBLEMA!!!!!!
	try:
		while True:
			now = datetime.now()
			if now >= tnow+tick:
				tnow = now+tick
				try:
					act = Decimal(scalperConf.client.get_symbol_ticker(symbol=symbol)["price"])
					#print(f"{symbol}: {act}")
					if act >= limit or act <= stop:
						if scalperConf.debug == False and scalperConf.shift == "True":
							scalperConf.client.order_market_sell(symbol=symbol, quantity=qty)
						print(f"{shift}: {symbol}- Trade cerrado en: {act:.8f}")
						putTraded(symbol, f"{act:.8f}",tradeShift)
						break
				except (exceptions.ConnectionError,
						exceptions.ConnectTimeout,
						exceptions.HTTPError,
						exceptions.ReadTimeout,
						exceptions.RetryError,
						SSL.Error,
						TypeError):
					print(f"{symbol}: Error en peticion, continuando.")
	except KeyboardInterrupt:
		if debug == False:
			client.order_market_sell(symbol=symbol, quantity=qty)
		print(f"{tradeShift}: {symbol}- Trade cerrado manualmente")
		putTraded(symbol, f"{act:.8f}",tradeShift)

class Scalper:
	"""En reconstruccion. Esto es un chocho. Mientras no haga push...
	"""
	def openTrade(self):
		msg = []
		bal = scalperConf.client.get_asset_balance(scalperConf.symbol)
		if Decimal(bal['free']) > Decimal(self.qtys["assetQty"]):
			if scalperConf.debug == False and scalperConf.shift == "True":
				msg.append(f"Ejecutando Orden de compra REAL {self.pair}")
				scalperConf.client.order_market_buy(symbol=self.pair, quantity=self.qtys["baseQty"])
				msg.append("Orden de compra ejecutada")
			else:
				msg.append(f"Ejecutando Orden de compra SIMULADA {self.pair}")
			rm.putTrading(self.pair,
						[f"{self.qtys['evalPrice']:{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*scalperConf.percentStop):{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*scalperConf.percentLimit):{self.data['precision']}}"],
						[f"{self.qtys['assetQty']}",
							f"{self.qtys['baseQty']}"])
		else:
			msg.append(f"Orden de compra {self.pair} no ejecutada. No hay suficiente cantidad de {scalperConf.symbol}")
		logger.log(msg, printFLAG=True)
	def startingAnalisys(self):
		"""[summary]
		"""
		check = checker.Checker(self)
		stage1 = check.stage1()
		if stage1 == True or self.force == True:
			self.dayKline = scalperConf.client.get_historical_klines(self.pair, scalperConf.Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
			act = Decimal(scalperConf.client.get_symbol_ticker(symbol= self.pair)["price"])
			self.qtys["evalPrice"] = act
			stage2 = check.stage2()
			if stage2 == True or self.force == True:
				if check.checkRules() == True:
					self.openTrade()
					self.monitor = True
					mesARR = [f"{datetime.now()}: {self.pair} MONITOR",
						f"--DAY min/med/max: {check.minDay:{self.data['precision']}} / {check.medDay:{self.data['precision']}} / {check.maxDay:{self.data['precision']}}",
						f"--Day grow: {check.growDay} %",
						f"--Entrada: {act:{self.data['precision']}}",
						f"--Limit: {((act/100)*scalperConf.percentLimit):{self.data['precision']}}",
						f"--Stop: {((act/100)*scalperConf.percentStop):{self.data['precision']}}"]
					logger.log(mesARR, printFLAG=True)
				else:
					logger.log([f"{datetime.now()}: {self.pair} NO SE CUMPLEN LAS REGLAS DE TRADING"], printFLAG=True)
					self.monitor = False
	def __init__(self, pair, min5Kline, force=False):
		self.data = pair
		self.data["minNotional"] = Decimal(self.data["minNotional"])
		self.data["minQty"] = Decimal(self.data["minQty"])
		self.data["stepSize"] = Decimal(self.data["stepSize"])
		self.data["precision"] = "."+self.data["precision"]+"f"
		self.pair = self.data["symbol"]
		self.min5Kline = min5Kline #kline de los ultimos 5 minutos, minuto a minuto.
		self.dayKline = None
		self.force = force
		self.monitor = False
		self.qtys = {"baseQty":"",
					"eurQty": "",
					"assetQty":"",
					"evalPrice": ""}
		self.startingAnalisys()
		if self.monitor == True:
			mon = multiprocessing.Process(target=monitor,
										args=(self.pair,
											Decimal((self.qtys["evalPrice"]/100)*scalperConf.percentLimit),
											Decimal((self.qtys["evalPrice"]/100)*scalperConf.percentStop),
											str(self.qtys["baseQty"]),),
										name= f"{scalperConf.shift}: {self.pair}")
			mon.daemon = True
			tradepool.append(mon)
			mon.start()


if __name__ == "__main__":
	rm = masterRequests.requestManager(scalperConf.masterIP, scalperConf.symbol, "scalper")
	logger = masterRequests.Logger(scalperConf.logname)
	logger.log([title], printFLAG=True)
	shiftTimes = rm.getBestShift(66)
	dtStart = datetime.now()
	shiftDelta = timedelta(days=1)
	logger.log([f"Proximos turnos a las: {shiftTimes['hour']}"], printFLAG=True)
	while True:
		cleanPools()
		dt = datetime.now()
		if dt-dtStart >= shiftDelta:
			dtStart = dtStart+shiftDelta
			shiftTimes = rm.getBestShift(66)
			logger.log([f"Proximos turnos a las: {shiftTimes['hour']}"], printFLAG=True)
		if str(dt.hour) in shiftTimes["hour"]:
			scalperConf.shift = "True"
			logger.log([f"Comenzando comprobacion {scalperConf.symbol}"], printFLAG=True)
			if len(tradepool) > 0:
				msg = f"Trades Abiertos:"
				for j in tradepool:
					msg = msg+ f"\n- {j.name}"
				logger.log([msg], printFLAG=True)
		else:
			scalperConf.shift = "False"
		try:
			tradeable = rm.getTradeable()
			for sym in tradeable:
				#print(sym)
				kline = scalperConf.client.get_historical_klines(sym["symbol"], scalperConf.Client.KLINE_INTERVAL_1MINUTE, "5 minutes ago UTC")
				if len(kline) > 0:
					a = Scalper(sym, kline)
		except (exceptions.ConnectionError,
				exceptions.ConnectTimeout,
				exceptions.HTTPError,
				exceptions.ReadTimeout,
				exceptions.RetryError,
				SSL.Error):
			logger.log(["Error, saltando a siguiente comprobacion"], printFLAG=True)