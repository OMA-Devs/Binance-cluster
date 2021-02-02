from datetime import datetime
from os import environ

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
	db = DB(dbName,client)
	a = db.getTRADINGdict()
	d = {"syms": a}
	return render(request, "trading.html", d)

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
		width=500,
		height=1200)
	div = plot(fig, output_type="div",
				include_plotlyjs=False,
				config={"displayModeBar": False,
						"autosizable": True})
	d = {"sym": sym, "graph": div}
	return render(request, "graphView.html", d)
