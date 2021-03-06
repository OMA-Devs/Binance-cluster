#!/usr/bin/env python3

'''checker.py'''

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