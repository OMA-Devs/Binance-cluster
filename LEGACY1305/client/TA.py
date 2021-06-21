#!/usr/bin/env python3

from os import environ
from binance.client import Client
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)

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
	#for line in newKline:
		#print(line)

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

class DojiSeeker:
	def currentTrend(self):
		#explain = f"---Identificando tendencia a 5 dias---" 
		#print(explain)
		firstClose = self.kline[0]["close"]
		lastClose = self.kline[-1]["close"]
		#print(f"firstClose: {firstClose}\nlastClose: {lastClose}")
		if firstClose > lastClose:
		#	print(f"Tendencia bajista confirmada")
			self.trend = "BEAR"
		else:
		#	print(f"Tendencia alcista confirmada")
			self.trend = "BULL"
		#print("-"*len(explain))
	def _shootingStar(self):
		relevantDoji = self.kline[-1]
		#print(relevantDoji)
		bodySize = 0
		wickSize = 0
		if relevantDoji["open"] > relevantDoji["close"]:
			bodySize = relevantDoji["open"]-relevantDoji["close"]
			wickSize = relevantDoji["high"]-relevantDoji["open"]
		else:
			bodySize = relevantDoji["close"]-relevantDoji["open"]
			wickSize = relevantDoji["high"]-relevantDoji["close"]
		#print(f"bodySize: {bodySize}\nwickSize: {wickSize}")
		if wickSize >= bodySize*2:
			print(f"{self.symbol}: Shooting Star identified")
		else:
			#print("Shooting Star missed")
			pass
	def _hammer(self):
		relevantDoji = self.kline[-1]
		#print(relevantDoji)
		bodySize = 0
		TOPwickSize = 0
		BOTwickSize = 0
		if relevantDoji["open"] > relevantDoji["close"]:
			bodySize = relevantDoji["open"]-relevantDoji["close"]
			TOPwickSize = relevantDoji["high"]-relevantDoji["open"]
			BOTwickSize = relevantDoji["close"]-relevantDoji["low"]
		else:
			bodySize = relevantDoji["close"]-relevantDoji["open"]
			TOPwickSize = relevantDoji["high"]-relevantDoji["close"]
			BOTwickSize = relevantDoji["open"]-relevantDoji["low"]
		#print(f"bodySize: {bodySize}\nTOPwickSize: {TOPwickSize}\nBOTwickSize: {BOTwickSize}")
		if TOPwickSize >= bodySize*2 and BOTwickSize <= bodySize:
			print(f"{self.symbol}: Inverted Hammer identified")
		elif BOTwickSize >= bodySize*2 and TOPwickSize <= bodySize:
			print(f"{self.symbol}: Hammer identified")
		else:
			#print("Hammer missed")
			pass
	def _piercing(self):
		d1 = self.kline[-1]
		d2 = self.kline[-2]
		if d2["open"] > d2["close"] and d1["close"] > d1["open"]:
			if d1["open"] <= d2["low"]:
				halfd2 = d2["close"] + ((d2["open"]-d2["close"])/2)
				if d1["close"] >= halfd2:
					print(f"{self.symbol}: Piercing identified")
				else:
					#print("Piercing Missed | Not above 50%")
					pass
			else:
				#print("Piercing Missed | d1 open above d2 low")
				pass
		else:
			#print("Piercing Missed | d2 not bearish or d1 not bullish")
			pass
	def searchReverseBull(self):
		self._shootingStar()
	def searchReverseBear(self):
		self._hammer()
		self._piercing()
	def __init__(self, symbol, kline, opMode):
		self.symbol = symbol
		self.kline = parseKline(kline)
		self.trend = None
		self.currentTrend()
		self.searchReverseBear()
		self.searchReverseBull()
		print(self.trend)

class Indicators:
	def getSMA(self):
		pass
	def getEMA(self):
		pass
	def getMACD(self):
		pass
	def __init__(self, symbol, kline):
		self.symbol = symbol
		self.kline = parseKline(kline)

class Worker:
	def __init__(self, symbol, task):
		self.symbol = symbol
		self.task = task
		if self.task == "doji":
			kline1d5p = client.get_historical_klines(self.symbol, Client.KLINE_INTERVAL_1DAY, "5 days ago")
			if kline1d5p > 0:
				dojis = DojiSeeker(self.symbol, kline, opMode)
			else:
				print(f"{self.symbol}- Imposible ejecutar DojiSeeker, no hay klines.")

if __name__ == "__main__":
	pass