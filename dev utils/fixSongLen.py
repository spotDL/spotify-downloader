from sys import argv as CLIARGS

from os import system as run_in_shell, walk
from os.path import join

rootDir = CLIARGS[1]
outDir = CLIARGS[2]

filePairs = (
    (join(root, file), join(outDir, file))
    for root, folders, files in walk(rootDir)
    for file in files
)


count = 0

cmd = 'ffmpeg -v quiet -y -i "%s" -acodec libmp3lame -abr true "%s"'

for pair in filePairs:
    run_in_shell(cmd % pair)
    print("%-3d %-100s" % (count, pair[1]), end="\r")
    count += 1
