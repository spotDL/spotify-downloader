
class Mgr():
    def __init__(self, name):
        self.name = name
    class new():
        def __init__(self, id, parent):
            self.id = id
            self.parent = parent
        def get(self):
            print(self.id, self.parent.name)
        def setName(self, name):
            self.parent.name = name
        def setId(self, id):
            self.id = id



if __name__ == "__main__":
    a = Mgr('asdf')
    b = a.new('1', a)
    b.get()
    b.setName('qwer')
    b.setId(2)
    b.get()