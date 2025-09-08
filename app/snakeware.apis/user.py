import json, pathlib

class SwUser:
    def __init__(self, filename: pathlib.Path):
        self._filename = pathlib.Path(filename)
        self._data = {}
    
    def __enter__(self):
        self.pull()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.push()
    
    def __contains__(self, value):
        return value in self._data
    
    def __iter__(self):
        return self._data.__iter__()

    def pull(self):
        if self._filename.exists():
            with open(self._filename, "r") as src:
                self._data = json.load(src)
        else:
            self._data = {}

    def push(self):
        with open(self._filename, "w") as src:
            json.dump(self._data, src)
    
    def get(self, key, default):
        return self._data.get(key, default)

    def getall(self):
        return self._data.copy()
    
    def set(self, key, value):
        return self._data.update({key: value})

    def update(self, value):
        return self._data.update(value)

_current_user: SwUser

def get_current_user():
    return _current_user

def set_current_user(src: pathlib.Path):
    _current_user = SwUser(src)
    _current_user.pull()