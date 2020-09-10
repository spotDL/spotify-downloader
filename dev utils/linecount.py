from sys import argv as CLIARGS
from os import walk
from os.path import join

rootdir = CLIARGS[1]

onlyErrors = False
onlyFails = False
ignoreFails = False

if '--only-errors' in CLIARGS:
    onlyErrors = True

if '--only-fails' in CLIARGS:
    onlyFails = True

if '--ignore-fails' in CLIARGS:
    ignoreFails = True

if onlyFails and ignoreFails:
    raise Exception('\n\nUse either --only-fails or --ignore-fails, not both...\n\n')

files = (
    join(dir, file)
        for dir, folders, files in walk(rootdir)
            for file in files
)

totalFiles = 0
correctFiles = 0
skips = 0

for eachFile in files:
    if not eachFile.endswith('.py'):
        continue

    totalFiles += 1
    
    linecount = 0
    inDocStr = False

    try:
        for cLine in open(eachFile, 'r').read().split('\n'):
            if cLine.strip().startswith("'''"):
                inDocStr = not inDocStr

            if not cLine.strip().startswith('#') and not inDocStr and cLine.strip() != '':
                linecount += 1
    except:
        if not ignoreFails:
            print("%-100s | ~~~~ | ~~~~ | ☠" % eachFile[-97:])
            skips += 1
    
    if linecount > 200:
        if not onlyFails:
            print("%-100s | %-4d | %-4d | ⚠" % (eachFile[-97:], linecount, linecount - 200))
    else:
        correctFiles += 1
        
        if not onlyErrors and not onlyFails:
            print("%-100s | %-4d | %-4d | ✔" % (eachFile[-97:], linecount, linecount - 200))

print('----------------------------------------------------------------------------------------------------------------')
print('TOTAL     %-4d\nSUCCESS   %-4d\nFAIL      %-4d\nSKIPPED   %-4d' % (
    totalFiles, correctFiles, totalFiles - correctFiles, skips
    )
)

# ffmpeg -y -v silent -i $inputFile  <-ar 44100> -af 'loudnorm=i=-17' $outFile