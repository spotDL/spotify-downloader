# Author: Mikhail Zex
# Status: Dropped (not in use, not in dev)

# About this file
'''
This file creates abstract classes implimenting the various interfaces defined
in 'Working Docs/interfaces.md' to ensure compliance to the interfaces.

Refer 'Working Docs/interfaces.md' for details on the interfaces, their inputs
and their outputs. The outputs of each of the abstractmethods defined here are
absolutely important as the other parts of the program work on assumptions
about the outputs.

Update: This file will not be making it into the finished version, for reasons
look to '11/08/2020 - 01:49 AM' in 'Working Docs.md'
'''

# Imports
from abc import ABCMeta, abstractmethod

# The Music Search Interface
class musicSearch(metaclass = ABCMeta):
    def implementsInterface(self):
        '''
        This method is an additional layer of security. Code utilizing 
        supposed realizations of various interface can call this method to
        check if they actually inherit from one of the predefined metaClasses.
        '''
        return True

    @abstractmethod
    def searchFromUri(self, spotifyUri):
        pass

    @abstractmethod
    def searchFromAllUri(self, spotifyUri):
        pass

    @abstractmethod
    def searchFromName(self, songName, artist = None):
        pass

    @abstractmethod
    def searchAllFromName(self, songName, artist = None):
        pass

# Metadata Search Interface
class metadataSearch(metaclass = ABCMeta):
    def implementsInterface(self):
        '''
        This method is an additional layer of security. Code utilizing 
        supposed realizations of various interface can call this method to
        check if they actually inherit from one of the predefined metaClasses.
        '''
        return True

    @abstractmethod
    def getDetails(self, song):
        pass

    @abstractmethod
    def getLyrics(self, song):
        pass