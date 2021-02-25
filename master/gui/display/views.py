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

def Trading(request):
	db = DB(dbName,client, request.GET["shift"])
	a = db.getTRADINGdict()
	d = {"syms": a}
	return render(request, "trading.html", d)

def Traded(request):
	db = DB(dbName,client, request.GET["shift"])
	a = db.getTRADEDdict()
	assets = [{"name": "ETH", "good": 0, "bad": 0, "percGood": 0, "benefit": 0},
				{"name": "BNB", "good": 0, "bad": 0, "percGood": 0, "benefit": 0}]
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
	general["percGood"] = (general["good"]/totTrades)*100
	general["duration"] = general["duration"]/totTrades

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
	hourRange = ["Noche (00-08)","Mañana (08-16)","Tarde (16-00)"]
	
	##Deteccion de ganancia o perdida
	for item in a:
		evalPrice = Decimal(item["evalPrice"])
		endPrice = Decimal(item["sell"])
		if endPrice > evalPrice:
			item["tradeEND"] = True
		else:
			item["tradeEND"] = False
	##Creacion de grafico de ganacia perdida por comienzo y final de Trade
	STAgoodBar = [0,0,0]
	STAbadBar = [0,0,0]
	ENDgoodBar = [0,0,0]
	ENDbadBar = [0,0,0]
	for item in a:
		STAhour = item["evalTS"].hour
		ENDhour = item["endTS"].hour
		if STAhour >= 0 and STAhour < 8:
			if item["tradeEND"] == True:
				STAgoodBar[0] = STAgoodBar[0]+1
			else:
				STAbadBar[0] = STAbadBar[0]+1
		elif STAhour >= 8 and STAhour < 16:
			if item["tradeEND"] == True:
				STAgoodBar[1] = STAgoodBar[1]+1
			else:
				STAbadBar[1] = STAbadBar[1]+1
		elif STAhour >= 16:
			if item["tradeEND"] == True:
				STAgoodBar[2] = STAgoodBar[2]+1
			else:
				STAbadBar[2] = STAbadBar[2]+1
		if ENDhour >= 0 and ENDhour < 8:
			if item["tradeEND"] == True:
				ENDgoodBar[0] = ENDgoodBar[0]+1
			else:
				ENDbadBar[0] = ENDbadBar[0]+1
		elif ENDhour >= 8 and ENDhour < 16:
			if item["tradeEND"] == True:
				ENDgoodBar[1] = ENDgoodBar[1]+1
			else:
				ENDbadBar[1] = ENDbadBar[1]+1
		elif ENDhour >= 16:
			if item["tradeEND"] == True:
				ENDgoodBar[2] = ENDgoodBar[2]+1
			else:
				ENDbadBar[2] = ENDbadBar[2]+1
	perTradeStart = go.Figure(data=[
		go.Bar(name="Ganados", x=hourRange, y=STAgoodBar),
		go.Bar(name="Perdidos", x=hourRange, y=STAbadBar)])
	perTradeStart.update_layout(barmode="group",title="Resultados agrupados por inicio del Trade")
	startTSdiv = plot(perTradeStart, output_type="div",
			include_plotlyjs=False,
			config={"displayModeBar": False,
					"autosizable": True})
	perTradeEnd = go.Figure(data=[
		go.Bar(name="Ganados", x=hourRange, y=ENDgoodBar),
		go.Bar(name="Perdidos", x=hourRange, y=ENDbadBar)])
	perTradeEnd.update_layout(barmode="group", title="Resultados agrupados por final del Trade")
	endTSdiv = plot(perTradeEnd, output_type="div",
			include_plotlyjs=False,
			config={"displayModeBar": False,
					"autosizable": True})
	####
	###Grafico de trades por pares.
	d = {"perStartTS": startTSdiv, "perEndTS": endTSdiv}
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
