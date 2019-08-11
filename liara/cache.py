import pathlib
import hashlib
import pickle
from typing import Dict
import os
import sqlite3


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


class Sqlite3Cache(Cache):
    """A :py:class:`Cache` implementation which uses SQLite to store the data.
    This is mostly useful if creating many files is slow, for instance due to
    anti-virus software.

    This cache tries to load a previously generated index. Use
    :py:meth:`persist` to write the cache index to disk.
    """

    def __init__(self, path: pathlib.Path):
        self.__path = path
        os.makedirs(self.__path, exist_ok=True)
        self.__db_file = self.__path / 'cache.db'
        self.__connection = sqlite3.connect(self.__db_file)
        self.__cursor = self.__connection.cursor()
        self.__cursor.execute("""CREATE TABLE IF NOT EXISTS cache
            (key BLOB PRIMARY KEY NOT NULL,
                data BLOB NOT NULL,
                object_type VARCHAR NOT NULL);""")

    def persist(self):
        """Persists this cache to disk.

        This function should be called after the cache has been populated. On
        the next run, the constructor will then pick up the index and return
        cached data.
        """
        self.__connection.commit()

    def put(self, key: bytes, value: object) -> bool:
        # The semantics are such that inserting the same key twice should not
        # cause a failure, so we ignore failures here
        q = 'INSERT OR IGNORE INTO cache VALUES(?, ?, ?);'

        # We check for byte(array), image nodes for instance store binary data
        # directly, and there's no need to send it through pickle. It doesn't
        # seem to make much of measurable difference though
        if isinstance(value, bytes) or isinstance(value, bytearray):
            object_type = 'BINARY'
        else:
            object_type = 'OBJECT'
            value = pickle.dumps(value)

        r = self.__cursor.execute(q, (key, value, object_type,))

        return r.lastrowid != 0

    def contains(self, key: bytes) -> bool:
        q = 'SELECT 1 FROM cache WHERE key=?'
        self.__cursor.execute(q, (key,))
        r = self.__cursor.fetchone()

        return r is not None

    def get(self, key: bytes) -> object:
        q = 'SELECT data, object_type FROM cache WHERE key=?'
        self.__cursor.execute(q, (key,))
        r = self.__cursor.fetchone()

        if r:
            if r[1] == 'OBJECT':
                return pickle.loads(r[0])
            else:
                return r[0]
        else:
            return None


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
