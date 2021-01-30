#!/usr/bin/env python3

import os
from binance.client import Client
from sys import argv
from decimal import Decimal

api_key = os.environ.get("TEST_BINANCE_API")
api_sec = os.environ.get("TEST_BINANCE_SEC")
real_api_key = os.environ.get("BINANCE_API_KEY")
real_api_sec = os.environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)

'''trades = client.get_my_trades(symbol="XVSBNB")
orders = client.get_all_orders(symbol = "XVSBNB")
price = Decimal(client.get_symbol_ticker(symbol="BNBEUR")["price"]) 
print(orders[0]["symbol"])
buyBASE = 0
sellBASE = 0
buy = ""
sell = ""
qty = 0
comision = 0
print("ORDERS")
for o in orders:
	print(o)
	print("\n")
print("-"*30)
print("TRADES")
for t in trades:
	print(t)
print("-"*30)

lastMarketOrderID = 0
for o in orders:
	if o["type"] =="MARKET":
		lastMarketOrderID = o["orderId"]
		break
tradesInOrder =[]
for t in trades:
	if t["orderId"] == lastMarketOrderID:
		tradesInOrder.append(t)
		print(tradesInOrder)'''

'''if o["isBuyer"] == True:
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
