import httpx


class SingletonHttpxClient(httpx.Client):
    globalClient = None
    initialized = False

    def __new__(cls, *args, **k):
        if cls.globalClient is None:
            print("inside globalclient")
            cls.globalClient = super().__new__(cls)
        return cls.globalClient

    def __init__(self, *args, **k):
        if not self.__class__.initialized:
            print("inside init")
            super().__init__(*args, **k)
            self.__class__.initialized = True


class Child(SingletonHttpxClient):
    def __init__(self, *args, **k):
        super().__init__(**k)
        print(args[0])


if __name__ == '__main__':
    for i in range(100):
        Child(i)
