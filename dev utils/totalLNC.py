from os.path import join
from os import walk
from sys import argv as CLIARGS

rootdir = CLIARGS[1]

if '-e' in CLIARGS or '--only-errors' in CLIARGS:
    onlyErrors = True
else:
    onlyErrors = False

if '-f' or '--fuzz' in CLIARGS:
    fuzzIndex = None
    
    if '-f' in CLIARGS:
        fuzzIndex = CLIARGS.index('-f')
    elif '--fuzz' in CLIARGS:
        fuzzIndex = CLIARGS.index('--fuzz')
    
    if fuzzIndex:
        fuzz = eval(CLIARGS[fuzzIndex + 1])
    else:
        fuzz = 0
    
    limit = 200 + fuzz

files = (
    join(dir, file)
        for dir, folders, files in walk(rootdir)
            for file in files
)

totalFiles = 0
correctFiles = 0
skipedFiles = 0

print('\n\n\nTOTAL LINE NUMBER COUNT (LNC)')
print('--------------------------------------------------------------' +
    '-----------------------------------------------------------------------')

for eachFile in files:
    if not eachFile.endswith('.py'):
        continue

    totalFiles += 1
    
    lineCount = 0
    inDocStr = False

    try:
        cLineNumber = 0

        for line in open(eachFile, 'r').read().split('\n'):
            strippedLine = line.strip()

            if strippedLine == '':
                continue

            if strippedLine.startswith("'''"):
                inDocStr = not inDocStr

            if strippedLine.startswith('def') and not inDocStr:
                bracketStartIndex = strippedLine.find('(')
                funcName = (strippedLine[4:bracketStartIndex], cLineNumber)
            
            elif not inDocStr:
                lineCount += int( len(line) / 90 ) + 1
                    
        if lineCount > limit:
            print ('| %-111s | %-4d | %-4d | ⚠ |' % (eachFile[-111:] , lineCount, lineCount - limit))
        else:
            if not onlyErrors:
                print ('| %-111s | %-4d | %-4d | ✔ |' % (eachFile[-111:] , lineCount, lineCount - limit))
            
            correctFiles += 1
        
        lineCount = {}

    except UnicodeDecodeError:
        print("| %-111s | ~~~~ | ~~~~ | ☠ |" % eachFile[-111:])
        skipedFiles += 1

print('--------------------------------------------------------------' +
    '-----------------------------------------------------------------------')
print('TOTAL %-4d\t\tSUCCESS %-4d\t\tFAIL %-4d\t\tSKIPPED %-4d' % (
    totalFiles, correctFiles, totalFiles - correctFiles, skipedFiles
    )
)
