#!/usr/bin/env python3

import requests
from client import AT, getTradeable
from datetime import datetime
from binance.client import Client
from os import environ

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

TEST_putTrading()