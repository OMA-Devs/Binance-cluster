#!/usr/bin/env python3

'''masterRequests'''

import requests
from datetime import datetime, timedelta
from ast import literal_eval

class Logger:
	def __init__(self, logname):
		self.logname = logname
		self.name = self.logname.split(".")[0]
	def log(self, mesARR, printFLAG = False):
		f = open(self.logname, "a+")
		for line in mesARR:
			st = f"{datetime.now()}|{self.name}| {line}\n"
			f.write(st)
			if printFLAG == True:
				print(st)
		f.close()


class requestManager:
	def __init__(self, masterIp, sym, cli):
		self.masterIP = masterIp
		self.sym = sym
		self.client = cli
		self.log = Logger(self.client+".log")
	def getTradeable(self, shift="ALL"):
		"""Hace una llamada al servidor maestro para obtener una lista de diccionario de todos los
		pares que se pueden tradear. El servidor se encarga de excluir los pares que ya estan en
		trading activo.

		Recibe una cadena de texto con la lista/diccionario como respuesta de la peticion y la evalua para
		generar la variable en cuestion. Si al intentar evaluar encuentra un error de sintaxis, eso
		significará que el servidor ha dado una respuesta de error en HTML y devolverá un array vacio.

		Returns:
			LIST: Lista de Diccionarios con los simbolos y sus reglas de trading.
		"""
		payload= {"sym": self.sym,
				"client": self.client}
		if self.client == "scalper":
			payload["shift"] = f"{shift}"
		r = requests.get('http://'+self.masterIP+'/data/getTradeable?', params=payload)
		text = r.text
		try:
			final = literal_eval(text)
			return final
		except SyntaxError:
			self.log.log(["No se puede obtener lista de trading de masterNode. Solicitando de nuevo."], printFLAG=True)
			return []
	def putTrading(self, pair, prices, qtys, shift="ALL"):
		"""Funcion que envia los datos del trade recien abierto al servidor central para almacenar
		en la base de datos.

		Args:
			pair (STR): Cadena del par cuyo trade se abre.
			prices (LIST): Lista de precios a almacenar en la base de datos. EvalPrice, stop y limit, en ese orden.
			qtys(LIST): Lista con las cantidades. ASSET es la moneda que usa el nodo para comprar. BASE es la moneda comprada.
		"""
		ts = str(datetime.timestamp(datetime.now()))
		payload = {"sym": pair,
					"evalTS": ts,
					"evalPrice": prices[0],
					"stop": prices[1],
					"limit": prices[2],
					"assetQty": qtys[0],
					"baseQty": qtys[1],
					"client": self.client}
		if self.client == "scalper":
			payload["shift"] = f"{shift}"
		r = requests.get("http://"+self.masterIP+"/data/putTrading?",params= payload)
		response = r.text
		if literal_eval(response) == True:
			if self.client == "scalper":
				self.log.log([f"{shift}| {pair}: Apertura de trade enviada a masterNode"], printFLAG=True)
			else:
				self.log.log([f"{pair}: Apertura de trade enviada a masterNode"], printFLAG=True)
		else:
			if self.client == "scalper":
				self.log.log([f"{shift}| {pair}: Apertura de trade no recibida en masterNode"], printFLAG=True)
			else:
				self.log.log([f"{pair}: Apertura de trade no recibida en masterNode"], printFLAG=True)
	def putTraded(self, pair, closePrice, shift="ALL"):
		"""Funcion que genera el request necesario para cerrar un trade en la base de datos del servidor.

		Args:
			pair (STR): Par a cerrar.
			closePrice (STR): Precio de cierre
			shift(BOOL): Turno del trade.
		"""
		ts = str(datetime.timestamp(datetime.now()))
		payload = {"sym": pair,
					"endTS": ts,
					"sellPrice": closePrice,
					"client": self.client
					}
		if self.client == "scalper":
			payload["shift"] = f"{shift}"
		r = requests.get("http://"+self.masterIP+"/data/putTraded?",params= payload)
		response = r.text
		if literal_eval(response) == True:
			if self.client == "scalper":
				self.log.log([f"{shift}|{pair}| Cierre enviado a masterNode"])
			else:
				self.log.log([f"{pair}| Cierre enviado a masterNode"])
		else:
			self.log.log([f"{pair}| Cierre no recibido en masterNode"])
	def getBestShift(self, minPerc):
		payload = {"minPerc": str(minPerc),
					"asset": self.sym}
		while True:
			r = requests.get('http://'+self.masterIP+'/data/getBestShift?', params=payload)
			text = r.text
			try:
				final = literal_eval(text)
				return final
			except SyntaxError:
				self.log.log(["No se puede obtener turno de masterNode. Solicitando de nuevo."])
