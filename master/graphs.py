#!/usr/bin/env python3

from os import environ
from binance.client import Client
#from dbOPS import DB
from sys import argv
import plotly.graph_objects as go
from time import sleep

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)

#db = DB("binance.db", client)
#assets = db.getTRADEABLE(argv[1])
#print(assets)

pair = argv[1]
kline = client.get_historical_klines(pair, Client.KLINE_INTERVAL_1HOUR, "1 day ago UTC")
df = {"Date":[],
	"Open": [],
	"High": [],
	"Low": [],
	"Close": []}
for line in kline:
	df["Date"].append(line[0])
	df["Open"].append(line[1])
	df["High"].append(line[2])
	df["Low"].append(line[3])
	df["Close"].append(line[4])

fig = go.Figure(data=[go.Candlestick(x=df['Date'],
				open=df['Open'],
				high=df['High'],
				low=df['Low'],
				close=df['Close'])])

obj = open("graph.html", "w")

fig.write_html(obj,
			full_html= False,
			include_plotlyjs= "../assets/plotly-latest.min.js",
			include_mathjax=False)

obj.close()
sleep(3)
'''obj = open("graph.html", "r")
print("HELLOOOOO")
for line in obj:
	print(line)
obj.close()'''


