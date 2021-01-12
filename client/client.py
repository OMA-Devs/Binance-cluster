#!/usr/bin/env python3

import requests
from os import environ
import config
from binance.client import Client
from binance.enums import *
from datetime import datetime, timedelta
from decimal import Decimal

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)

def logger(logName, mesARR):
	f = open("logs/"+logName+".log", "a+")
	for line in mesARR:
		f.write(line+"\n")
		print(line)
	f.close()

def parseSTRtoLIST(text):
	stageA = text[1:-2]
	stageB = stageA.split(",")
	stageC = []
	for i in stageB:
		stageC.append(i.strip(" '"))
	return stageC

def getTradeable():
	payload= {"sym": config.symbol}
	r = requests.get('http://'+config.masterIP+config.masterPATH+'/getSym.php', params=payload)
	text = r.text
	final = parseSTRtoLIST(text)
	return final

def openTrade(pair, sym, lim, sto):
	eurP = Decimal(client.get_symbol_ticker(symbol=sym+"EUR")["price"])
	act = Decimal(client.get_symbol_ticker(symbol=pair)["price"])
	qty = 5/eurP
	for bal in client.get_account()["balances"]:
		if bal["asset"] == sym:
			if Decimal(bal['free']) > qty:
				print("Ejecutando Orden de compra")
				client.order_market_buy(symbol=pair, quantity=f"{qty:.5f}")
	for bal in client.get_account()["balances"]:
		if bal["asset"] == pair.strip(sym):
			print("Emplazando Orden OCO")
			qty = bal["free"]
			qtySTR = f"{qty:.5f}"
			client.create_oco_order(symbol=pair, side=SIDE_SELL, stopLimitTimeInForce=TIME_IN_FORCE_GTC,
				quantity=qtySTR,
				stopPrice=f"{((act/100)*sto):.5f}",
				price=f"{((act/100)*lim):.5f}")

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
	def getDay(self):
		"""Calcula las estadisticas referentes al día
		"""
		MinMax = self._getMinMax(self.dayKline)
		self.minDay = MinMax[0]
		self.maxDay = MinMax[1]
		self.medDay = self._getMedium(self.dayKline)
		self.growDay = self._getPercentage(self.dayKline)
	def getHour(self):
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
		if self.monitor == True:
			act = Decimal(self.client.get_symbol_ticker(symbol= self.pair)["price"])
			if (act/100)*self.limitPrice < self.maxDay and act <= (self.medDay/100)*self.limitPrice:
				print(self.pair+"- STAGE 2- Cualifica")
				openTrade(self.pair,config.symbol,self.limitPrice,self.stopPrice)
				logName = self.pair+"-"+str(datetime.now().date())
				mesARR = ["-"*60,
					self.pair+" MONITOR",
					str(datetime.now()),
					"DAY min/med/max: "+ f"{self.minDay:.15f}"+" / "+f"{self.medDay:.15f}"+" / "+f"{self.maxDay:.15f}",
					"HOUR min/med/max: "+ f"{self.min1h:.15f}"+" / "+f"{self.med1h:.15f}"+" / "+f"{self.max1h:.15f}",
					"Day/1h grow: "+ str(self.growDay)+"% / "+str(self.grow1hTOT)+"%",
					"Entrada:"+f"{act:.15f}",
					"Limit: "+f"{((act/100)*self.limitPrice):.15f}",
					"Stop: "+f"{((act/100)*self.stopPrice):.15f}"]
				for line in self.grow1h[-3:]:
					mesARR.append("--: "+str(line)+"%")
				logger(logName, mesARR)
			else:
				self.monitor = False
	def __init__(self, client, pair, dayKline):
		"""[summary]

		Args:
			client ([type]): [description]
			pair ([type]): [description]
			monitorPERC ([type]): [description]
		"""
		if len(dayKline) > 0:
			#print("NOT IN TRADING")
			self.client = client
			self.pair = pair
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
			self.monitor = False
			self.limitPrice = 105 # Porcentaje maximo para salir de la posicion.
			self.stopPrice = 95 # Porcentaje minimo para vender.
			self.getHour()
			self.getDay()
			#self.setLimits()
			self.startingAnalisys()
		else:
			self.monitor = False



if __name__ == "__main__":
	while True:
		tradeable = getTradeable()
		print("Comenzando comprobacion "+config.symbol+": "+str(datetime.now()))
		for sym in tradeable:
			#print(sym)
			kline = client.get_historical_klines(sym, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
			a = AT(client, sym, kline)

	