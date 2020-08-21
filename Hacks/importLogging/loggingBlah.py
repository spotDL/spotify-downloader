import logging

# Note,
# 
# The purpose of a log is not to provide the utmost information, it is to provide
# the bare minimum required information to diagnose the problem. It is for those
# reasons that  details like time (asctime), module name (module) were removed as
# the module name doesn't necessarily provide the level of nesting (eg, 
# logingBase > Blah > module might simply show up as just module) and can cause
# confunsion between similarly named but different files.
#
# Time for our purpose is irrelevant. The module name has been replaced by the
# more accurate file path + line number. The function (funcName) name has been
# retained as a quick reference ( its easier to recall than file path + line
# number). The logger name has been retained as an extra measure for quick
# identification.
#
# Also, guidelines for assigning logging levels?

logging.basicConfig(
    filename = 'spotdl.log',
    filemode = 'w',
    format = '%(levelname)-10s | %(process)-7s | %(name)-20s | %(message)-150s | %(funcName)-20s | %(pathname)s (ln:%(lineno)d)',
    level = logging.INFO
)

# CRITICAL      --> Errors that can't/shouldn't be handled
# ERROR         --> Exceptions (errors that are being handled)
# WARNING       --> Actions supposed to be done, cant be done
# INFO          --> What is being done, decision + result
# DEBUG
# NOTSET

# CRITICAL logs to stderr
criticalHandler = logging.StreamHandler() #--> also seems useless
criticalHandler.setLevel(logging.CRITICAL)
#fileHandler = logging.FileHandler('.log') --> not required

formater = logging.Formatter('TERMINAL ERROR: %(message)s')
criticalHandler.setFormatter(formater)

log0 = logging.getLogger('test')
#log0.addHandler(criticalHandler)

log1 = logging.getLogger('test.loggingBlah')

log0.info('first message')
log1.info('first message')

log0.critical('this should  be part of stderr')
log1.critical('this should also be part of stderr')

log1.debug('this should not even register')
log1.warning('debug message from log.loggingBlah was not registered, repeating message after reseting level')

log1.setLevel(logging.NOTSET) # Not working, why? Cuz its set to NOTSET
log1.debug('this debug message should, in theory, register')

log1.setLevel(logging.DEBUG)
log1.debug('this debug message should, in theory, register')

def randFN(message):
    log0.info('Message sent to randFN - '+ message)

def getMyLogger(name):
    return logging.getLogger('test.' + name)