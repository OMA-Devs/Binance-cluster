#!/usr/bin/env python3

import requests
from clientNEW import AT, Checker, getTradeable
from datetime import datetime, timedelta
from binance.client import Client
from os import environ
from decimal import Decimal

import multiprocessing
from random import randint

real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
debug = True
tradepool= []

def TEST_putTrading():
	syms = getTradeable()
	for i in range(1):
		rnd = randint(0, len(syms))
		kline = client.get_historical_klines(syms[rnd]["symbol"], Client.KLINE_INTERVAL_1MINUTE, "5 minutes ago UTC")
		if len(kline) > 0 :
			AT(client, syms[rnd], kline, force=True)
	print(tradepool)

def TEST_getAsset(asset):
	print(client.get_asset_balance(asset))

def main_loop():
	jobs = []
	lap = timedelta(seconds=5)
	tnow = datetime.now()
	while True:
		now = datetime.now()
		if now > tnow+lap:
			print("Procesos abiertos: ")
			for ind, j in enumerate(jobs):
				if j.is_alive() == False:
					jobs.pop(ind)
			for j in jobs:
				print("- "+ j.name+ " "+ str(j.is_alive()))
			num = randint(1,11)
			tnow = now
			print("Main loop")
			if num%2 == 0:
				print("Numero PAR")
				s = multiprocessing.Process(target=worker, args=(num,), name="Proceso Hijo "+str(num))
				jobs.append(s)
				s.daemon = True
				s.start()

def worker(num):
	name = multiprocessing.current_process().name
	#print("Comenzando worker: "+name)
	lap = timedelta(seconds=2)
	tnow = datetime.now()
	while True:
		now = datetime.now()
		if now > tnow+lap:
			tnow = now
			n = randint(1,11)
			if n == num:
				#print("Numero generado, terminando proceso.")
				break
	print(name+" Terminado")

def TEST_checkRules(inv):
	syms = getTradeable()
	sym = None
	for i in syms:
		if i["symbol"] == "WINBNB":
			sym = i
	act = Decimal(client.get_symbol_ticker(symbol=sym["symbol"])["price"])
	eurP = Decimal(client.get_symbol_ticker(symbol="BNBEUR")["price"])
	invBNB = inv/eurP ##Precio de inversion minima en moneda ASSET
	startQTY = invBNB/act ##CANTIDAD de moneda BASE
	notionalValue = startQTY*act
	stepCheck = (startQTY-Decimal(sym["minQty"]))%Decimal(sym["stepSize"])
	print(sym["precision"])
	if stepCheck != 0:
		startQTY = startQTY-stepCheck
		stepCheck = (startQTY-Decimal(sym["minQty"]))%Decimal(sym["stepSize"])
		notionalValue = startQTY*act
		if stepCheck == 0 and notionalValue >= Decimal(sym["minNotional"]):
			print("stepCheck PASSED. Reajustado")
			print("minNotional PASSED.")
			print(f"QTY: {startQTY}")
			print(f"BNB: {(startQTY*act):.{sym['precision']}f}")
			print(f"EUR: {(startQTY*act)*eurP:.{sym['precision']}f}")
	else:
		print("stepCheck PASSED")
		if notionalValue >= Decimal(sym["minNotional"]):
			print("minNotional PASSED")
		else:
			print("minNotional NOT PASSED")
	#print(act)
	#print(invBNB)
	#print(startQTY)


TEST_checkRules(20)