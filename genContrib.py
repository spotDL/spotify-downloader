from re import findall
from asyncio import run
from time import perf_counter

from json import dumps

import asks

looked_up_users = {}


async def get_public_user_data(username):
    if username in looked_up_users:
        return looked_up_users[username]

    print(f'looking up @{username}')

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

    looked_up_users[username] = datavalues

    return datavalues

async def get_table_row(user_list):
    markdown = "<tr>\n"

    for user in user_list:
        userdata = await get_public_user_data(user)

        markdown += '\t<td align="center">\n'

        avatar_link = userdata["avatar"]
        markdown += f'\t\t<img src="{avatar_link}" width="100px"/>\n\t\t<br/>\n'

        name = userdata["name"]
        username = userdata["username"]
        markdown += f"\t\t{name} (@{username})\n\t\t<br/>\n"

        github_profile_link = userdata["githubProfile"]
        markdown += f'\t\t<a href="{github_profile_link}">github</a>\n'

        if userdata["website"]:
            website_link = userdata["website"]
            markdown += f'\t\t| <a href="{website_link}">website</a>\n'

        if userdata["twitter"]:
            twitter = userdata["twitter"]
            markdown += f'\t\t| <a href="{twitter}">twitter</a>\n'

        markdown += "\t</td>\n"

    markdown += "</tr>\n"

    return markdown

async def get_contributing_for_given_version(user_list, version):

    if not version == "latest":
        markdown = f'<details>\n<summary>\n\n## v{version}\n</summary>\n\n<table align="center">'
    else:
        markdown = f'## Latest Release\n\n<table align="center">'

    user_list.sort()

    for i in range(0, len(user_list), 4):
        table_row = await get_table_row(user_list[i : i + 4])
        markdown += f"\n{table_row}"

    markdown += "\n</table>"

    if not version == "latest":
        markdown += "\n</details>"

    return markdown

async def get_contributing():
    contributing_data = eval(open("CONTRIBUTORS", "r").read())
    key_list = list(contributing_data.keys())
    key_list.remove("latest")
    key_list.sort(reverse=True)

    version_contributors = contributing_data['latest']
    version_contributors.sort()

    markdown = await get_contributing_for_given_version(
        version_contributors, 'latest'
    )

    for version in key_list:
        version_contributors = contributing_data[version]
        version_contributors.sort()

        markdown += await get_contributing_for_given_version(
            version_contributors, version
        )

    return markdown.replace('## v2', '## Upto v2.2.2')

async def print_contributing():
    q = await get_contributing()
    print(q)

st = perf_counter()
run(print_contributing())
time = perf_counter() - st

print(f'\n\nTIME TAKEN: {time}')