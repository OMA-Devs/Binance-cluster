from datetime import datetime, timedelta
from os import environ
from decimal import Decimal

import plotly.graph_objects as go
from binance.client import Client
from django.http import HttpResponse
from django.shortcuts import render
from plotly.offline import plot

from dbOPS import DB

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
dbName = "/var/www/html/Binance/master/binance.db"

def index(request):
	return render(request, "index.html")

def Trading(request):
	db = DB(dbName,client, request.GET["shift"])
	a = db.getTRADINGdict()
	d = {"syms": a}
	return render(request, "trading.html", d)

def Traded(request):
	db = DB(dbName,client, request.GET["shift"])
	a = db.getTRADEDdict()
	assets = [{"name": "ETH", "good": 0, "bad": 0, "percGood": 0, "benefit": 0},
				{"name": "BNB", "good": 0, "bad": 0, "percGood": 0, "benefit": 0},
				{"name": "BTC", "good": 0, "bad": 0, "percGood": 0, "benefit": 0}]
	general = {"good": 0, "bad":0,"percGood":0, "duration": timedelta(seconds= 0)}
	for item in a:
		evalPrice = Decimal(item["evalPrice"])
		endPrice = Decimal(item["sell"])
		if endPrice > evalPrice:
			item["tradeEND"] = True
			general["good"] = general["good"] +1
		else:
			item["tradeEND"] = False
			general["bad"] = general["bad"] +1
		item["duration"] = item["endTS"]-item["evalTS"]
		general["duration"] = general["duration"] + item["duration"]

	totTrades = general["good"]+general["bad"]
	try:
		general["percGood"] = (general["good"]/totTrades)*100
		general["duration"] = general["duration"]/totTrades
	except ZeroDivisionError:
		general["percGood"] = 0
		general["duration"] = 0

	for asset in assets:
		Lass = len(asset["name"])
		for item in a:
			if item["symbol"][Lass-Lass*2:] == asset["name"]:
				if item["tradeEND"] == True:
					asset["good"] = asset["good"] + 1
				else:
					asset["bad"] = asset["bad"] + 1
				soldAT = Decimal(item["sell"])*Decimal(item["baseQty"])
				ben = soldAT-Decimal(item["assetQty"])
				asset["benefit"] = asset["benefit"] + ben
		totTrades = asset["good"]+asset["bad"]
		asset["percGood"] = (asset["good"]/totTrades)*100

	d = {"syms": a, "assets": assets, "general": general}
	return render(request, "traded.html", d)

def Stats(request):
	db = DB(dbName,client, request.GET["shift"])
	a = db.getTRADEDdict()
	###VARIABLES PARA EL GRAFICO DE PERDIDOS/GANADOS
	hourRange = []
	STAgoodBar = [] #Lista de ganadores
	STAbadBar = [] #Lista de perdedores
	for i in range(24):
		hourRange.append(f"H{i}")
		STAgoodBar.append(0)
		STAbadBar.append(0)
	################################################
	##Deteccion de ganancia o perdida
	for item in a:
		evalPrice = Decimal(item["evalPrice"])
		endPrice = Decimal(item["sell"])
		if endPrice > evalPrice:
			item["tradeEND"] = True
		else:
			item["tradeEND"] = False
	##Creacion de grafico de ganacia perdida por comienzo de Trade
	for item in a:
		STAhour = item["evalTS"].hour
		if item["tradeEND"] == True:
			STAgoodBar[STAhour] = STAgoodBar[STAhour] + 1
		else:
			STAbadBar[STAhour] = STAbadBar[STAhour] + 1
	perTradeStart = go.Figure(data=[
		go.Bar(name="Ganados", x=hourRange, y=STAgoodBar),
		go.Bar(name="Perdidos", x=hourRange, y=STAbadBar)])
	perTradeStart.update_layout(barmode="group",title="Resultados agrupados por inicio del Trade")
	startTSdiv = plot(perTradeStart, output_type="div",
			include_plotlyjs=False,
			config={"displayModeBar": False,
					"autosizable": True})
	####
	###VARIABLES PARA EL GRAFCO POR PARES
	parList = []
	winList = []
	losList = []
	for item in a:
		try:
			ind = parList.index(item["symbol"])
		except ValueError:
			parList.append(item["symbol"])
			winList.append(0)
			losList.append(0)
			ind = parList.index(item["symbol"])
		if item["tradeEND"] == True:
			winList[ind] = winList[ind] + 1
		else:
			losList[ind] = losList[ind] + 1
	###Grafico de trades por pares.
	perPair = go.Figure(data=[
		go.Bar(name="Ganados", x=winList, y=parList, orientation= "h"),
		go.Bar(name="Perdidos", x=losList, y=parList, orientation="h")])
	perPair.update_layout(barmode="group",title="Resultados agrupados por Pares",
						height=3000)
	perPairdiv = plot(perPair, output_type="div",
			include_plotlyjs=False,
			config={"displayModeBar": False,
					"autosizable": True})
	###############################
	d = {"perStartTS": startTSdiv, "perPair": perPairdiv}
	return render(request, "stats.html", d)

def Graph(request):
	sym = request.GET["sym"]
	kline = client.get_historical_klines(sym, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
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
	fig.update_layout(
		autosize=True,
		width=800,
		height=1200)
	div = plot(fig, output_type="div",
				include_plotlyjs=False,
				config={"displayModeBar": False,
						"autosizable": True})
	db = DB(dbName,client, request.GET["shift"])
	syms = db.getTRADINGdict()
	symDATA = None
	for i in syms:
		if i["symbol"] == sym:
			symDATA = i
	d = {"sym": sym, "graph": div, "data": symDATA}
	return render(request, "graphView.html", d)
