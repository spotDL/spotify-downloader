from ytmusicapi import YTMusic

client = YTMusic()

res = client.search("IL5842236126", ignore_spelling=True, filter="songs")

print(res)
