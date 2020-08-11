from abc import ABCMeta, abstractproperty, abstractmethod

class testInterface(metaclass = ABCMeta):
    def implementsInterface(self):  # this is inherited like normal
        return True

    @abstractmethod     # it2 arg is useless, item arg is similarly non-binding
    def push(self,item, it2=None):  # code in abstract methods are useless too.
        print(it2)
        print('is it2\n')
        pass

    @abstractmethod
    def pop(self):
        '''
        returns a song object for the best match of the song whose spotifyURI
        is provided as 'link'.
        '''
        pass
    
    @abstractproperty
    def size(self):
        pass

class implementInterface(testInterface):
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)
        #print(it2)

    def pop(self):
        return self.items.pop()
    
    @property           # properties are special functions that are called like
    def size(self):     # attributes
        return len(self.items)

test = implementInterface()
test.push(2) #error if print(it2) is not commentedout
print(test.size)
print(test.pop.__doc__) # prints 'None', not the docstring.
print(test.implementsInterface())