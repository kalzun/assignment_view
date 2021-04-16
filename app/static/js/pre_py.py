from browser.local_storage import storage
import _io
import os


def mock_os_remove(path):
    if mock_exists(path):
        del storage[path]


def mock_exists(path):
    return bool(storage.get(path))


def mock_rename(src, dst):
    if mock_exists(src):
        storage[dst] = storage.pop(src)



class MockFile(_io.TextIOWrapper):
    # Mocking file read/write

    def __init__(self, name=None, mode=None, content=None):
        self.name = name
        self.mode = mode
        self.content = content
        self.stream_pos = 0
        self.place = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        pass

    def write(self, data):
        if self.mode == "w" or self.mode == "a":
            self.content += data
            storage[self.name] = self.content
        else:
            raise IOError("read only")

    def read(self, n=None):
        if self.name in storage and n is None:
            return storage[self.name]
        elif self.name in storage and n > 0:
            self.stream_pos += n
            if len(self.content) > self.stream_pos:
                return storage[self.name][self.stream_pos - 1]
            else:
                return ""
        else:
            raise IOError("file not found")

    def readline(self):
        self.place = self.content.find("\n")
        if self.place == -1:
            len_content = len(self.content)
            if len_content > 0:
                line = self.content[:]
                self.content = self.content[len_content:]
                self.stream_pos += len_content + 1
            else:
                line = ""
        else:
            line = self.content[: self.place]
            self.stream_pos += self.place + 1
            # remove first line
            self.content = self.content[self.place + 1 :]
        return line

    def readlines(self):
        all_lines = []
        line = self.readline()
        while line != "":
            all_lines.append(line + "\n")
            line = self.readline()
        return all_lines

    def tell(self):
        return self.stream_pos

    def __iter__(self):
        for line in self.readlines():
            yield line

    def close(self):
        return


def mock_open(name, mode="r", encoding="utf-8"):
    if mode == "w":
        storage[name] = ""
    content = storage[name]
    return MockFile(name, mode, content)


os.rename = mock_rename
os.path.exists = mock_exists
os.remove = mock_os_remove
open = mock_open
