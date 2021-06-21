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

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)

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
	payload= {"sym": "BTC",
			"shift": True}
	r = requests.get('http://'+config.masterIP+'/data/getTradeable?', params=payload)
	text = r.text
	try:
		final = literal_eval(text)
		return final
	except SyntaxError:
		print("No se puede obtener lista de trading de masterNode. Solicitando de nuevo.")
		return []

class DojiSeeker:
	def parseKline(self):
		newKline = []
		for candle in self.kline:
			newCandle = {
				"openTime": datetime.fromtimestamp(candle[0]/1000),
				"open": Decimal(candle[1]),
				"high": Decimal(candle[2]),
				"low": Decimal(candle[3]),
				"close": Decimal(candle[4])
			}
			newKline.append(newCandle)
		self.kline = newKline
		#for line in newKline:
			#print(line)
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
		self.kline = kline
		self.trend = None
		self.parseKline()
		self.currentTrend()
		if opMode == "BUY":
			if self.trend == "BEAR":
				#explain = f"---Buscando cambios a alcista---"
				#print(explain)
				self.searchReverseBear()
				#print("-"*len(explain))
		elif opMode == "SELL":
			if self.trend == "BULL":
				#explain = f"---Buscando cambios a bajista---"
				#print(explain)
				self.searchReverseBull()
				#print("-"*len(explain))

if __name__ == "__main__":
	'''Insertamos la fecha del dia del analisis. No usar fecha actual. NO PODRIAMOS
	COMPROBAR LA TENDENCIA QUE DETERMINA EL PROGRAMA
	day = int(input("Inserta el día: "))
	month = int(input("Inserta el mes: "))
	year = int(input("Inserta el año: "))
	signalDate = datetime(year, month, day)'''
	day = 25
	month = 3
	year = 2021
	signalDate = datetime(year, month, day)
	#print(signalDate)
	'''Rango de días que vamos a solicitar ANTERIORES a la fecha dada para designar
	la tendencia'''
	dayRange = timedelta(5)
	yesterday = datetime.today()-timedelta(1)
	#print(signalDate-dayRange)
	'''Obtenemos el kline correspondiente al rango a analizar'''
	#kline = client.get_historical_klines("ADAEUR",Client.KLINE_INTERVAL_1DAY, str(yesterday-dayRange), str(yesterday))
	#DS = DojiSeeker(kline)

	tradeable = getTradeable()
	for sym in tradeable:
		print(sym["symbol"])
		kline = client.get_historical_klines(sym["symbol"], Client.KLINE_INTERVAL_1DAY, str(yesterday-dayRange), str(yesterday))
		if len(kline) > 0:
			a = DojiSeeker(sym["symbol"], kline, "BUY")