#!/usr/bin/env python3

import requests
from client import putTrading
from datetime import datetime

ts = str(datetime.timestamp(datetime.now()))
payload = {"sym":"BTCEUR", "startTS": ts}
putTrading(payload)