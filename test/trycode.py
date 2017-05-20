class acls():
    def func(self):
        self.bcls().func()
        print("class a func")
    class bcls():
        def func(self):
            print("class b func")


# acls().func()
acls.bcls().func()