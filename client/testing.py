#!/usr/bin/env python3

import requests
from client import AT, getTradeable
from datetime import datetime, timedelta
from binance.client import Client
from os import environ

import multiprocessing
from random import randint

real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
debug = True

def TEST_putTrading():
	syms = getTradeable()
	for sym in syms:
		kline = client.get_historical_klines(sym["symbol"], Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
		if len(kline) > 0 :
			AT(client, sym, kline, force=True)
			break

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


main_loop()