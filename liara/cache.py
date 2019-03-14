import pathlib
import hashlib
import pickle
from typing import Dict
import os


class Cache:
    """A key-value cache."""
    def put(self, key: bytes, value: object) -> bool:
        """Put a value into the cache using the provided key.

        :param key: The key under which ``value`` will be stored.
        :param value: A pickable Python object to be stored.
        :return: ``True`` if the value was added to the cache, ``False`` if
                 it was already cached.
        """
        return True

    def contains(self, key: bytes) -> bool:
        """Check if an object is stored.

        :param key: The key to check.
        :return: ``True`` if such an object exists, else ``False``.
        """
        return False

    def get(self, key: bytes) -> object:
        """Get a stored object.

        :param key: The object key.
        :return: An object if one exists. Otherwise, the behavior is undefined.
                 Use :py:meth:`contains` to check if an object exists.
        """
        return None


class FilesystemCache(Cache):
    """A :py:class:`Cache` implementation which uses the filesystem to cache
    data.

    This cache tries to load a previously generated index. Use
    :py:meth:`persist` to write the cache index to disk.
    """
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
        """Persists this cache to disk.

        This function should be called after the cache has been populated. On
        the next run, the constructor will then pick up the index and return
        cached data.
        """
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
    """An in-memory :py:class:`Cache` implementation.

    This cache stores all objects in-memory.
    """
    __index: Dict[bytes, object]

    def __init__(self):
        self.__index = {}

    def contains(self, key: bytes) -> bool:
        return key in self.__index

    def put(self, key: bytes, value: object) -> bool:
        if key in self.__index:
            return False

        self.__index[key] = object
        return True

    def get(self, key: bytes) -> object:
        return self.__index[key]