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

# Reasons behind the basic configuration for loggers can be found at .
logging.basicConfig(
    filename = 'spotdl.log',
    filemode = 'w',
    format = '%(levelname)-10s | %(name)-20s | %(message)-150s | \
        %(funcName)-20s | %(pathname)s (ln:%(lineno)d)',
    level = logging.INFO
)

# Use stream handler to selectively print CRITICAL logs to cmd-line
# formatter formats CRITICAL log for the cmd-line
formater = logging.Formatter('TERMINAL ERROR: %(message)s')

# Create the handler, set formating using a formater
criticalHandler = logging.StreamHandler()
criticalHandler.setLevel(logging.CRITICAL)
criticalHandler.setFormatter(formater)

# This log is the topmost log in the heirarchal logger being created.
topLog = logging.getLogger('spotdl')
topLog.addHandler(criticalHandler)

topLog.info('All defined loggers have been configured')