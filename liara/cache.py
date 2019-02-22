import pathlib
import hashlib
import pickle
from typing import Dict
import os


class Cache:
    def put(self, key: bytes, value: object) -> bool:
        return True

    def contains(self, key: bytes) -> bool:
        return False

    def get(self, key: bytes) -> object:
        return None

class FilesystemCache(Cache):
    __index: Dict[bytes, pathlib.Path]

    def __init__(self, path: pathlib.Path):
        self.__path = path
        self.__index = {}
        os.makedirs(self.__path, exist_ok=True)
        self.__index_file = self.__path / 'cache.index'
        if self.__index_file.exists():
            try:
                self.__index = pickle.load(self.__index_file.open('rb'))
            except Exception:
                # Not being able to load the cache is not an error
                pass

    def persist(self):
        pickle.dump(self.__index, self.__index_file.open('wb'))

    def put(self, key: bytes, value: object) -> bool:
        if key in self.__index:
            return False

        cache_object_path = self.__path / hashlib.sha256(key).hexdigest()
        pickle.dump(value, cache_object_path.open('wb'))

        self.__index[key] = cache_object_path
        return True

    def contains(self, key: bytes) -> bool:
        return key in self.__index

    def get(self, key: bytes) -> object:
        cache_object_path = self.__index[key]
        return pickle.load(cache_object_path.open('rb'))


class MemoryCache(Cache):
    __index: Dict[bytes, object]

    def __init__(self):
        self.__index = {}

    def contains(self, key: bytes) -> bool:
        return key in self.__index

    def put(self, key: bytes, value: object) -> bool:
        if key in self.__index:
            return False

        self.__index[key] = object

    def get(self, key: bytes) -> object:
        return self.__index[key]