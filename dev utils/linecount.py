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
            print("%-100s | ~~~~ | ☠" % eachFile[-100:])
            skips += 1
    
    if linecount > 200:
        if not onlyFails:
            print("%-100s | %04d | ⚠" % (eachFile[-100:], linecount))
    else:
        correctFiles += 1
        
        if not onlyErrors and not onlyFails:
            print("%-100s | %04d | ✔" % (eachFile[-100:], linecount))

print('----------------------------------------------------------------------------------------------------------------')
print('TOTAL     %04d\nSUCCESS   %04d\nFAIL      %04d\nSKIPPED   %04d' % (
    totalFiles, correctFiles, totalFiles - correctFiles, skips
    )
)