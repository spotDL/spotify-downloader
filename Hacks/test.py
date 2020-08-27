fileName = input('fileName: ')
q = eval(open( fileName + '.txt', 'rb').read().decode().replace('false', 'False').replace('true', 'True').replace('null', 'None'))

file = open(fileName + '.skeleton.txt', 'wb')
maxInd = 0

def pprint(JSON, indent = 0):
    global file
    global maxInd

    if indent > maxInd:
        maxInd = indent
    
    if isinstance(JSON, list) and len(JSON) > 0:
        for each in JSON:
            outStr = ''

            for i in range(indent):
                outStr += '\t'
            
            outStr += ('%02d:\n' % JSON.index(each))
            print(outStr, end='')
            file.write(outStr.encode())
            pprint(each, indent=indent+1)

    elif isinstance(JSON, dict) and len(JSON) > 0:
        for key, value in JSON.items():
            outStr = ''

            for i in range(indent):
                outStr += '\t'

            outStr += ('%s:\n' % key)
            print(outStr, end='')
            file.write(outStr.encode())
            pprint(value, indent=indent+1)

pprint(q)
file.close()

print()
print(maxInd)