#!/usr/bin/env python3

import os
from binance.client import Client
from dbOPS import DB
from sys import argv

api_key = os.environ.get("TEST_BINANCE_API")
api_sec = os.environ.get("TEST_BINANCE_SEC")
real_api_key = os.environ.get("BINANCE_API_KEY")
real_api_sec = os.environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)

db = DB("binance.db", client)
assets = db.getTRADEABLE(argv[1])
print(assets)

