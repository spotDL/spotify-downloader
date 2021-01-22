from re import findall
from asyncio import run
from time import perf_counter

from json import dumps

import asks

usernames = ["mikhailZex", "Silverarmor", "phcreery", "aasmpro", "loftwah", "BaseMax"]


async def get_public_user_data(username):
    datavalues = {}

    datahead = await asks.get(f"https://github.com/{username}")
    data = datahead.content.decode()

    name_list = findall('<span.+itemprop="name">(.+)</span>', data)

    if name_list != []:
        datavalues["name"] = name_list[0]
    else:
        datavalues["name"] = username

    datavalues["username"] = username

    links = findall('<a rel="nofollow me".+href="(.+)">.+</a>', data)

    for link in links:
        if "twitter" in link:
            datavalues["twitter"] = link
        else:
            datavalues["website"] = link

    if "twitter" not in datavalues.keys():
        datavalues["twitter"] = None
    if "website" not in datavalues.keys():
        datavalues["website"] = None

    datavalues["githubProfile"] = f"https://github.com/{username}"

    datavalues["avatar"] = findall('<img.+alt="Avatar".+src="(.+)".+/>', data)[0]

    return datavalues


async def print_all_as_jason():
    for username in usernames:
        data_values = await get_public_user_data(username)
        print(dumps(data_values, sort_keys=True, indent="  "))
        print("----------")

st = perf_counter()
run(print_all_as_jason())
print(perf_counter() - st)
