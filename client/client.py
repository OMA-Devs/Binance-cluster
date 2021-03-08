#!/usr/bin/env python3

import requests
from os import environ, system
from sys import argv
import config
from config import debug
from binance.client import Client
from binance.enums import SIDE_SELL, TIME_IN_FORCE_GTC
from datetime import datetime, timedelta
from decimal import Decimal
from ast import literal_eval
import multiprocessing
from OpenSSL import SSL

title = '''
____ ____ ____ _    ___  ____ ____ 
[__  |    |__| |    |__] |___ |__/ 
___] |___ |  | |___ |    |___ |  \\
'''

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
shift = None

tradepool = []

def cleanPools():
	for ind,j in enumerate(tradepool):
		if j.is_alive() == False:
			tradepool.pop(ind)

def logger(logName, mesARR):
	"""Funcion de logging para simplificar los logs del sistema.
	Decidi no usar el modulo logging pues el conocimiento que tengo
	no cubre el uso que quiero hacer de él.

	Cuando se ejecuta la funcion, tambien escribe en la terminal los mensajes.
	Esto es para acelerar la ejecucion.

	Args:
		logName (STR): Nombre del log. El formato es PAR-str(datetime) sin extension.
		mesARR (LIST): Lista de mensajes a loggear.
	"""
	f = open(f"logs/{logName}.log", "a+")
	for line in mesARR:
		f.write(f"{line}\n")
		if shift == True:
			print(line)
		else:
			pass
	f.close()

def getBestShift(minPerc, asset):
	payload = {"minPerc": str(minPerc),
				"asset": config.symbol}
	r = requests.get('http://'+config.masterIP+'/data/getBestShift?', params=payload)
	text = r.text
	try:
		final = literal_eval(text)
		return final
	except SyntaxError:
		print("No se puede obtener turno de masterNode. Solicitando de nuevo.")
		while True:
			r = requests.get('http://'+config.masterIP+'/data/getBestShift?', params=payload)
			text = r.text
			try:
				final = literal_eval(text)
				return final
			except SyntaxError:
				print("No se puede obtener turno de masterNode. Solicitando de nuevo.")

def getTradeable():
	"""Hace una llamada al servidor maestro para obtener una lista de diccionario de todos los
	pares que se pueden tradear. El servidor se encarga de excluir los pares que ya estan en
	trading activo.

	Recibe una cadena de texto con la lista/diccionario como respuesta de la peticion y la evalua para
	generar la variable en cuestion. Si al intentar evaluar encuentra un error de sintaxis, eso
	significará que el servidor ha dado una respuesta de error en HTML y devolverá un array vacio.

	Returns:
		LIST: Lista de Diccionarios con los simbolos y sus reglas de trading.
	"""
	payload= {"sym": config.symbol,
			"shift": str(shift)}
	r = requests.get('http://'+config.masterIP+'/data/getTradeable?', params=payload)
	text = r.text
	try:
		final = literal_eval(text)
		return final
	except SyntaxError:
		print("No se puede obtener lista de trading de masterNode. Solicitando de nuevo.")
		return []

def putTrading(sym, prices, qtys):
	"""Funcion que envia los datos del trade recien abierto al servidor central para almacenar
	en la base de datos.

	Args:
		sym (STR): Cadena del par cuyo trade se abre.
		prices (LIST): Lista de precios a almacenar en la base de datos. EvalPrice, stop y limit, en ese orden.
		qtys(LIST): Lista con las cantidades. ASSET es la moneda que usa el nodo para comprar. BASE es la moneda comprada.
	"""
	ts = str(datetime.timestamp(datetime.now()))
	payload = {"sym": sym,
				"evalTS": ts,
				"evalPrice": prices[0],
				"stop": prices[1],
				"limit": prices[2],
				"assetQty": qtys[0],
				"baseQty": qtys[1],
				"shift": shift}
	r = requests.get("http://"+config.masterIP+"/data/putTrading?",params= payload)
	response = r.text
	if literal_eval(response) == True:
		print(f"{sym}: Apertura de trade enviada a masterNode")
	else:
		print(f"{sym}: Apertura de trade no recibida en masterNode")

def putTraded(sym, closePrice, tradeShift):
	"""Funcion que genera el request necesario para cerrar un trade en la base de datos del servidor.

	Args:
		sym (STR): Par a cerrar.
		closePrice (STR): Precio de cierre
	"""
	ts = str(datetime.timestamp(datetime.now()))
	payload = {"sym": sym,
				"endTS": ts,
				"sellPrice": closePrice,
				"shift": str(tradeShift)
				}
	r = requests.get("http://"+config.masterIP+"/data/putTraded?",params= payload)
	response = r.text
	if literal_eval(response) == True:
		print("Trade enviado a masterNode")
	else:
		print("Trade no recibido en masterNode")

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
	tradeShift = shift
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
						print(f"{shift}: {symbol}- Trade cerrado en: {act:.8f}")
						putTraded(symbol, f"{act:.8f}",tradeShift)
						break
				except (requests.exceptions.ConnectionError,
						requests.exceptions.ConnectTimeout,
						requests.exceptions.HTTPError,
						requests.exceptions.ReadTimeout,
						requests.exceptions.RetryError,
						SSL.Error,
						TypeError):
					print(f"{symbol}: Error en peticion, continuando.")
	except KeyboardInterrupt:
		if debug == False:
			client.order_market_sell(symbol=symbol, quantity=qty)
		print(f"{tradeShift}: {symbol}- Trade cerrado manualmente")
		putTraded(symbol, f"{act:.8f}",tradeShift)

class Checker:
	"""Antigua clase ALGO. Esta clase engloba las comprobaciones de los
	datos de la clase AT y determina si un par cualifica o no para un trade.

	Por el momento, la comprobación se compone de 2 etapas.
	"""
	def __init__(self, at):
		"""Metodo de inicialización. Recibe simplemente una instancia de AT
		para trabajar con sus datos.

		Args:
			at (AT): Instancia de AT sobre la que ejecutar comprobaciones.
		"""
		self.at = at
	def stage1(self):
		"""Comprueba el crecimiento en los ultimos 5 minutos y detecta crecimientos
		con un sistema de pesos. Si el peso final supera el umbral, se determina
		que el par pasa la primera etapa.

		Returns:
			BOOL: True si cualifica. False si no lo hace.
		"""
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
			if shift == True:
				print(self.at.pair+"-STAGE 1- Cualifica")
			#print("---"+ str(self.at.min5grow))
			return True
		else:
			#print(self.at.pair+": NO Cualifica PESO: "+str(weight))
			#print("---"+ str(self.at.min5grow))
			return False
	def stage2(self):
		"""Segunda etapa. Con los datos diarios comprueba si el precio actual
		se encuentra en unos limites seguros de compra. Las comprobaciones que
		efectua son:
			1- Comprueba que el precio limite determinado NO es superior al maximo diario.
			2- Comprueba que el precio de evaluacion no es superior a la media diaria+porcentaje limite.

		Returns:
			BOOL: True si cualifica. False si no lo hace.
		"""
		limitPrice = (self.at.qtys["evalPrice"]/100)*self.at.limitPrice
		if limitPrice < self.at.maxDay:
			marginAVG = (self.at.medDay/100)*self.at.limitPrice
			if self.at.qtys["evalPrice"] <= marginAVG:
				if shift == True:
					print(self.at.pair+"- STAGE 2- Cualifica")
				return True
			else:
				#print(f"{self.at.pair} - STAGE 2 NO Cualifica. Precio actual superior a media+limit: {marginAVG:{self.at.data['precision']}}")
				return False
		else:
			#print(self.at.pair+"- STAGE 2- NO Cualifica. Limit por encima del maximo diario: "+f"{limitPrice:{self.at.data['precision']}}")
			return False

class AT:
	"""Clase de analisis tecnico. Ejecuta la clasificacion de los datos y luego el algoritmo de cualificacion
	y, si cumplen los parametros, ejecuta la funcion monitor en un proceso paralelo.
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
			kline (LIST): Lista de Kline.

		Returns:
			LIST: Lista con los crecimientos.
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
		"""Comprueba las reglas de trading. Tras una actualizacion, ya no se utiliza un bucle WHILE que puede
		durar horas dependiendo del par.
		Aun no me gusta la funcion, pero es impresionantemente mas rapida y solo necesita una mejoría de la
		gestion de los bucles if para no tener segmentos de codigo repetidos y manejar alguna excepcion excepcional.
		Las reglas de trading, segun las define la API de Binance, son las siguientes:
			- filtro minNotional: el filtro minNotional se obtiene con (price*quantity)
			- filtro marketLot: este filtro se supera con las siguientes condiciones
				- quantity >= minQty
				- quantity <= maxQty
				- (quantity-minQty) % stepSize == 0
		"""
		act = Decimal(client.get_symbol_ticker(symbol=self.pair)["price"])
		eurP = Decimal(client.get_symbol_ticker(symbol=f"{config.symbol}EUR")["price"])
		invASSET = self.maxINV/eurP ##Precio de inversion minima en moneda ASSET
		startQTY = invASSET/act ##CANTIDAD de moneda BASE
		notionalValue = startQTY*act
		stepCheck = (startQTY-self.data["minQty"])%self.data["stepSize"]
		if stepCheck != 0:
			startQTY = startQTY-stepCheck
			stepCheck = (startQTY-self.data["minQty"])%self.data["stepSize"]
			notionalValue = startQTY*act
			if stepCheck == 0 and notionalValue >= Decimal(sym["minNotional"]):
				'''print("stepCheck PASSED. Reajustado")
				print("minNotional PASSED.")'''
				self.qtys["baseQty"] = f"{startQTY:{self.data['precision']}}"
				self.qtys["eurQty"] = f"{(startQTY*act)*eurP:{self.data['precision']}}"
				self.qtys["assetQty"] = f"{notionalValue:{self.data['precision']}}"
				'''msg = [f"Trading Rules Check PASSED",
						"Price:"+f"{act:{self.data['precision']}}",
						"EUR TO TRADE: "+f"{self.qtys['eurQty']}",
						config.symbol+" TO TRADE: "+f"{notionalValue:{self.data['precision']}}",
						"qty: "+f"{startQTY:{self.data['precision']}}",
						"-"*30]
				logger(self.logName, msg)'''
				return True
			else:
				'''msg = [f"stepCheck/notionalValue NOT PASSED"]
				logger(self.logName, msg)'''
				return False
		else:
			'''print("stepCheck PASSED")'''
			if notionalValue >= Decimal(sym["minNotional"]):
				print("minNotional PASSED")
				self.qtys["baseQty"] = f"{startQTY:{self.data['precision']}}"
				self.qtys["eurQty"] = f"{(startQTY*act)*eurP:{self.data['precision']}}"
				self.qtys["assetQty"] = f"{notionalValue:{self.data['precision']}}"
				'''msg = [f"Trading Rules Check PASSED",
						"Price:"+f"{act:{self.data['precision']}}",
						"EUR TO TRADE: "+f"{self.qtys['eurQty']}",
						config.symbol+" TO TRADE: "+f"{notionalValue:{self.data['precision']}}",
						"qty: "+f"{startQTY:{self.data['precision']}}",
						"-"*30]
				logger(self.logName, msg)'''
				return True
			else:
				'''print("minNotional NOT PASSED")'''
				self.qtys["baseQty"] = f""
				self.qtys["eurQty"] = f""
				self.qtys["assetQty"] = f""
				'''print("Trading Rules Check NOT PASSED. Check de loop.")'''
				return False
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
						[f"{self.qtys['evalPrice']:{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*self.stopPrice):{self.data['precision']}}",
							f"{((self.qtys['evalPrice']/100)*self.limitPrice):{self.data['precision']}}"],
						[f"{self.qtys['assetQty']}",
							f"{self.qtys['baseQty']}"])
		else:
			msg.append(f"Orden de compra no ejecutada. No hay suficiente cantidad de {config.symbol}")
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
				if self.checkRules() == True:
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
				else:
					print("NO SE CUMPLEN LAS REGLAS DE TRADING")
					self.monitor = False
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
		self.maxINV = config.eurINV #Inversion maxima en EUR. Se considerara cantidad minima segun las reglas de trading.
		self.force = force
		self.monitor = False
		self.logName = self.pair+"-"+str(datetime.now().date())
		self.limitPrice = 107 # Porcentaje maximo para salir de la posicion.
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
										args=(self.pair,
											Decimal((self.qtys["evalPrice"]/100)*self.limitPrice),
											Decimal((self.qtys["evalPrice"]/100)*self.stopPrice),
											str(self.qtys["baseQty"]),),
										name= f"{shift}: {self.pair}")
			mon.daemon = True
			tradepool.append(mon)
			mon.start()


if __name__ == "__main__":
	print(title)
	shiftTimes = getBestShift(75, config.symbol)
	dtStart = datetime.now()
	shiftDelta = timedelta(days=1)
	print(f"Proximos turnos a las:")
	for h in shiftTimes["hour"]:
		print(f"- {h}")
	while True:
		cleanPools()
		dt = datetime.now()
		if dt-dtStart >= shiftDelta:
			dtStart = dtStart+shiftDelta
			shiftTimes = getBestShift(75, config.symbol)
			print(f"Proximos turnos a las:")
			for h in shiftTimes["hour"]:
				print(f"- {h}")
		if str(dt.hour) in shiftTimes["hour"]:
			shift = "True"
			print("Comenzando comprobacion "+config.symbol+": "+str(datetime.now()))
			if len(tradepool) > 0:
				print("Trades Abiertos:")
				for j in tradepool:
					print("- "+ j.name)
		else:
			shift = "False"
		try:
			tradeable = getTradeable()
			for sym in tradeable:
				#print(sym)
				kline = client.get_historical_klines(sym["symbol"], Client.KLINE_INTERVAL_1MINUTE, "5 minutes ago UTC")
				if len(kline) > 0:
					a = AT(client, sym, kline)
		except (requests.exceptions.ConnectionError,
				requests.exceptions.ConnectTimeout,
				requests.exceptions.HTTPError,
				requests.exceptions.ReadTimeout,
				requests.exceptions.RetryError,
				SSL.Error):
			print("Error, saltando a siguiente comprobacion")