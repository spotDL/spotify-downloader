from sys import argv as CLIARGS

onlyCount = False

if "--only-count" in CLIARGS or "-oc" in CLIARGS:
    onlyCount = True

print()

for eachFile in CLIARGS[1:]:
    if eachFile.endswith(".spotdlTrackingFile"):
        dumps = eval(open(eachFile, "rb").read().decode())

        songCount = 0

        for dump in dumps:
            songCount += 1

            songName = dump["rawTrackMeta"]["name"]

            contributingArtists = ""

            for artist in dump["rawTrackMeta"]["artists"]:
                if artist["name"].lower() not in songName.lower():
                    contributingArtists += artist["name"] + ", "

            if not onlyCount:
                print(
                    "%3d   %-60s   %s" % (songCount, contributingArtists[:-2], songName)
                )

        print("Found search results")

        print('\nThere are %d songs in "%s"' % (songCount, eachFile[2:-19]))
