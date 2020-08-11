# Author: Mikhail Zex
# Status: Dev

# About this file
'''
This file creates abstract classes implimenting the various interfaces defined
in 'Working Docs/interfaces.md' to ensure compliance to the interfaces.

Refer 'Working Docs/interfaces.md' for details on the interfaces, their inputs
and their outputs. The outputs of each of the abstractmethods defined here are
absolutely important as the other parts of the program work on assumptions
about the outputs.
'''

# Imports
from abc import ABCMeta, abstractmethod

# The Music Search Interface
class musicSearchInterface(metaclass = ABCMeta):
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
class metadataSearchInterface(metaclass = ABCMeta):
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