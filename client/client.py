#!/usr/bin/env python3

import requests
import config

def parseSTRtoLIST(text):
	stageA = text[1:-2]
	stageB = stageA.split(",")
	stageC = []
	for i in stageB:
		stageC.append(i.strip(" '"))
	return stageC


payload= {"sym": config.symbol}
r = requests.get('http://'+config.masterIP+config.masterPATH+'/getSym.php', params=payload)
text = r.text
final = parseSTRtoLIST(text)
print(final)