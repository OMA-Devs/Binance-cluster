#!/usr/bin/env python3

import os
from binance.client import Client
from dbOPS import DB
from sys import argv
from decimal import Decimal

api_key = os.environ.get("TEST_BINANCE_API")
api_sec = os.environ.get("TEST_BINANCE_SEC")
real_api_key = os.environ.get("BINANCE_API_KEY")
real_api_sec = os.environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)

db = DB("binance.db", client)
assets = db.getTRADEABLE(argv[1])
print(assets)

'''orders = client.get_my_trades(symbol="XVSBNB")
price = Decimal(client.get_symbol_ticker(symbol="BNBEUR")["price"]) 
print(orders[0]["symbol"])
buyBASE = 0
sellBASE = 0
buy = ""
sell = ""
qty = 0
comision = 0
for o in orders:
	print(o)
	print("\n")
if o["isBuyer"] == True:
		qty = o["qty"]
		comision = comision + Decimal(o["commission"])
		buyBASE = o["quoteQty"]
		print("PRECIO COMPRA: "+ o["price"])
	elif o["isMaker"] == True and o["qty"] == qty:
		comision = comision + Decimal(o["commission"])
		sellBASE = o["quoteQty"]
		print("PRECIO VENTA: "+ o["price"])
bruto = Decimal(sellBASE)-Decimal(buyBASE)
neto = (Decimal(sellBASE)-Decimal(buyBASE))-comision
print("Beneficio Bruto: "+f"{bruto} BNB | {bruto*price:.2f} EUR")
print("Beneficio Neto: "+f"{neto} BNB | {neto*price:.2f} EUR")'''
