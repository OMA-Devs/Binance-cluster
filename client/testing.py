#!/usr/bin/env python3

import requests
from client import putTrading
from datetime import datetime
from binance.client import Client
from os import environ

def TEST_putTrading(sym):
	putTrading(sym)

def TEST_getAsset(asset):
	real_api_key = environ.get("BINANCE_API_KEY")
	real_api_sec = environ.get("BINANCE_API_SEC")
	client = Client(real_api_key,real_api_sec)
	print(client.get_asset_balance(asset))