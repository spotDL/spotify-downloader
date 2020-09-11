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
    
    limit = 100 + fuzz

files = (
    join(dir, file)
        for dir, folders, files in walk(rootdir)
            for file in files
)

totalClasses = 0
correctClasses = 0
skipedFiles = 0

print('\n\n\nCLASS LINE NUMBER COUNT (LNC)')
print('--------------------------------------------------------------' +
    '-----------------------------------------------------------------------')

for eachFile in files:
    if not eachFile.endswith('.py'):
        continue

    lineCount = {}

    inDocStr = False
    inClass = False

    classBaseIndent = 0
    className = ''

    try:
        cLineNumber = 0

        for line in open(eachFile, 'r').read().split('\n'):
            cLineNumber += 1
            
            line = line.replace('\t', '    ')
            strippedLine = line.strip()

            baseIndent = len(line) - len(strippedLine)

            if strippedLine == '':
                continue

            if strippedLine.startswith("'''"):
                inDocStr = not inDocStr

            if strippedLine.startswith('class') and not inDocStr:
                bracketStartIndex = strippedLine.find('(')
                className = (strippedLine[6:bracketStartIndex], cLineNumber)

                classBaseIndent = baseIndent
                inClass = True

                totalClasses += 1
                lineCount[className] = 0
            
            elif baseIndent > classBaseIndent and inClass != 0 and not inDocStr and className != '':
                lineCount[className] += 1
            
            elif baseIndent < classBaseIndent:
                inClass = False
        
        for classDetails, lineLen in lineCount.items():
            className, line = classDetails

            if lineLen > limit:
                print ('| %-75s %-35s | %-4d | %-4d | ⚠ |' % ((eachFile + ':%d' % line)[-75:] , className[:35], lineLen, lineLen - limit))
            else:
                if not onlyErrors:
                    print ('| %-75s %-35s | %-4d | %-4d | ✔ |' % ((eachFile + ':%d' % line)[-75:] , className[:35], lineLen, lineLen - limit))
                
                correctClasses += 1
        
        lineCount = {}

    except UnicodeDecodeError:
        print("| %-111s | ~~~~ | ~~~~ | ☠ |" % eachFile[-111:])
        skipedFiles += 1

print('--------------------------------------------------------------' +
    '-----------------------------------------------------------------------')
print('TOTAL %-4d\t\tSUCCESS %-4d\t\tFAIL %-4d\t\tSKIPPED %-4d' % (
    totalClasses, correctClasses, totalClasses - correctClasses, skipedFiles
    )
)
