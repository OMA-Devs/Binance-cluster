#!/usr/bin/env python3

from os import environ
from binance.client import Client

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)


masterIP = "192.168.1.43"
#masterPATH = "/Binance/master/"
symbol = "BNB"
eurINV = 20
percentLimit = 107
percentStop = 95

logname = "scalper.log"
shift = None
debug = True