from abc import ABC
from abc import abstractmethod

class AuthorizeBase(ABC):
    """
    Defined service authenticators must inherit from this abstract
    base class and implement their own functionality for the below
    defined methods.
    """

    @abstractmethod
    def authorize(self):
        """
        This method must authorize with the corresponding service
        and return an object that can be utilized in making
        authenticated requests.
        """
        pass

