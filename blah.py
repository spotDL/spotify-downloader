from typing import final
import urllib.request as requrl
from re import findall

username = "mikhailZex"

data = requrl.urlopen(f"https://github.com/{username}")
dataq = ""

x = 0

for line in data:
    x += 1
    bah = line.decode()

    if bah.strip() != "":
        dataq += bah

    if x == 500:
        break

while True:
    q = input('re:')
    print(findall(q, dataq))
    print()