import logBlah

masterClass = None

class randomCrap(object):
    def __init__(self):
        global masterClass              # without this, masterClass be none
        masterClass = logBlah.rClass()

q = randomCrap()

if None: print('blah')
if 12: print('blah blah')

print(masterClass)

print(logBlah.__dict__)