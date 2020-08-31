# Different log levels in decreasing order of importance and their uses within
# spot-dl:
#   -CRITICAL   > Errors that can't/shouldn't be handled
#   -ERROR      > Exceptions (Errors that can and are being handled)
#   -WARNING    > Actions that are supposed to be done but can't be
#   -INFO       > Overview of what is being done at any given point
#   -DEBUG      > Not in use
#   -NOTSET     > Not in use
#
# Please note that this file will be updated often during dev, the very purpose
# of isolating the logging settings here is to be able to manage what could
# possibly be a large number of loggers.

'''
This file is the one spot configuration to set up heirarchal logging.
'''

#===============
#=== Imports ===
#===============
import logging



#=================
#=== Main Code ===
#=================

# Reasons behind the basic configuration for loggers can be found at 
# .Working Docs/Design Notes.md

logging.basicConfig(
    filename = 'spotdl.log',
    filemode = 'w',
    format = '%(levelname)-10s | %(process)d | %(name)-20s | %(message)-150s' +
    '| %(funcName)-20s | %(pathname)s (ln:%(lineno)d)',
    level = logging.INFO
)

# Use stream handler to selectively print CRITICAL logs to cmd-line
# formatter formats CRITICAL log for the cmd-line
formater = logging.Formatter('TERMINAL ERROR: %(message)s\n\n\n')

# Create the handler, set formating using a formater
criticalHandler = logging.StreamHandler()
criticalHandler.setLevel(logging.CRITICAL)
criticalHandler.setFormatter(formater)

# This log is the topmost log in the heirarchal logger being created.
topLog = logging.getLogger('spotdl')
topLog.addHandler(criticalHandler)

# Function passing out requisite loggers to various modules
def getSubLoggerFor(functionalUnit):
    '''
    `str` `functionalUnit` : one of ['authorization', 'utility', 'other', 'tests']

    Returns a logger related to the functionality of the module calling
    this function.
    '''
    
    # Mapping of module function to logger name
    loggerMap = {
        'authorization': 'spotdl.authorize',
        'utility': 'spotdl.utility',
        'tests': 'spotdl.test',
        'other': 'spotdl.other'
    }

    return logging.getLogger(loggerMap[functionalUnit])

# Log initialization
topLog.info('All defined loggers have been configured')