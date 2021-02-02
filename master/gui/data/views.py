from django.shortcuts import render
from django.http import HttpResponse

from binance.client import Client

from dbOPS import DB

import plotly.graph_objects as go
from plotly.offline import plot

from sys import argv
from os import environ, getcwd, listdir
import json
from sqlite3 import OperationalError
from datetime import datetime

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
dbName = "/var/www/html/Binance/master/binance.db"

def index(request):
	return render(request, "content.html")

def exampleGraph(request):
	kline = client.get_historical_klines("BTCEUR", Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
	df = {"Date":[],
		"Open": [],
		"High": [],
		"Low": [],
		"Close": []}
	for line in kline:
		df["Date"].append(datetime.fromtimestamp(line[0]/1000))
		df["Open"].append(line[1])
		df["High"].append(line[2])
		df["Low"].append(line[3])
		df["Close"].append(line[4])
	fig = go.Figure(data=[go.Candlestick(x=df['Date'],
				open=df['Open'],
				high=df['High'],
				low=df['Low'],
				close=df['Close'])])
	div = plot(fig, output_type="div")
	return HttpResponse(div)

def getTradeable(request):
	db = DB(dbName, client)
	tradeable = db.getTRADEABLE(request.GET["sym"])
	return HttpResponse(json.dumps(tradeable))

def putTrading(request):
	db = DB(dbName, client)
	symbol = request.GET["sym"]
	startTS = request.GET["startTS"]
	db.tradeSTART(symbol,startTS)
	try:
		return HttpResponse(str(True))
	except OperationalError:
		####COMPRUEBA LOS PERMISOS DE LA BASE DE DATOS!!!!
		return HttpResponse(str(False))

def viewTrading(request):
	db = DB(dbName,client)
	a = db.getTRADINGdict()
	d = {"syms": a}
	return render(request, "trading.html", d)

