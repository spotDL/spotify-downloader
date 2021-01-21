from typing import final
import urllib.request as requrl
from re import findall
from asyncio import run
from time import perf_counter

import asks

usernames = [
    "mikhailZex",
    "Silverarmor",
    "phcreery",
    "aasmpro",
    "loftwah",
    "BaseMax"
]
async def getUserData(username):
    datavalues = {}

    datahead = await asks.get(f"https://github.com/{username}")
    data = datahead.content.decode()

    datavalues['name'] = findall('<span.+itemprop="name">(.+)</span>', data)
    datavalues['username'] = findall('<span.+itemprop="additionalName">(.+)</span>', data)
    datavalues['publicLinks'] = findall('<a rel="nofollow me".+href="(.+)">.+</a>', data)
    datavalues['imageLink'] = findall('<img.+alt="Avatar".+src="(.+)".+/>', data)

    return datavalues

async def printAll():
    for username in usernames:
        datavals = await getUserData(username)
        print(datavals)

st = perf_counter()
run(printAll())
print(perf_counter() - st)