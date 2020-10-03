from __clitest__ import progresstest5

class A():
    def __init__(self):
        self.name = "asdf"
        self.helpr = Helper(self)

    def yo(self):
        return Helper(self)
    
    def func(self):
        print(self.name)
    


class Helper(A):
    def __init__(self, parent):
        self.help = True
        self.parent = parent

    def go(self):
        print('Help:', self.parent.name, self.help)

a = A()
a.func()
b = a.yo()
b.go()

# Helper.go()