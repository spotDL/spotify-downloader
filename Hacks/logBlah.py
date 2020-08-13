import importLogging.loggingBlah as Blah

# log2 = Blah.getMyLogger(__name__) can also be used that might not be such a
# good idea because it imposes rules on written code.
log2 = Blah.logging.getLogger('test.logBlah')

def funcNameTest():
    log2.info('This message is from the outer file')

funcNameTest()

class rClass(object):
    def __init__(self): pass

    def classFNameTest(self):
        log2.info('This message is from the outer file')

q = rClass()
q.classFNameTest()

Blah.randFN('This message was sent from the outer file')