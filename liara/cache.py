import pathlib
import hashlib
import pickle
from typing import Dict, Optional
import os
import sqlite3
from datetime import timedelta


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

    def get(self, key: bytes) -> Optional[object]:
        """Get a stored object.

        :param key: The object key.
        :return: An object if one exists. Otherwise, return ``None``.
        """
        return None

    def persist(self) -> None:
        """Persists this cache to disk/persistent storage.

        This function should be called after the cache has been populated. On
        the next run, the constructor will then pick up the index and return
        cached data.
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
        pickle.dump(self.__index, self.__index_file.open('wb'))

    def put(self, key: bytes, value: object) -> bool:
        if key in self.__index:
            return False

        cache_object_path = self.__path / hashlib.sha256(key).hexdigest()
        pickle.dump(value, cache_object_path.open('wb'))

        self.__index[key] = cache_object_path
        return True

    def get(self, key: bytes) -> Optional[object]:
        if key not in self.__index:
            return None

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

    def get(self, key: bytes) -> Optional[object]:
        q = 'SELECT data, object_type FROM cache WHERE key=?'
        self.__cursor.execute(q, (key,))
        r = self.__cursor.fetchone()

        if r:
            if r[1] == 'OBJECT':
                return pickle.loads(r[0])
            else:
                return r[0]

        return None


class MemoryCache(Cache):
    """An in-memory :py:class:`Cache` implementation.

    This cache stores all objects in-memory.
    """
    __index: Dict[bytes, object]

    def __init__(self):
        self.__index = {}

    def put(self, key: bytes, value: object) -> bool:
        if key in self.__index:
            return False

        self.__index[key] = object
        return True

    def get(self, key: bytes) -> Optional[object]:
        return self.__index.get(key, None)


class RedisCache(Cache):
    """A cache using Redis as the storage backend."""

    def __init__(self, host: str, port: int, db: int,
                 expiration_time=timedelta(hours=1)):
        import redis
        self.__redis = redis.Redis(host, port, db)
        self.__expiration_time = expiration_time

    def __make_key(self, key: bytes, suffix: str) -> str:
        return f'liara/{key.hex()}/{suffix}'

    def put(self, key: bytes, value: object) -> bool:
        if isinstance(value, bytes) or isinstance(value, bytearray):
            object_type = 'bin'
        else:
            object_type = 'obj'
            value = pickle.dumps(value)

        self.__redis.set(self.__make_key(key, 'content'),
                         value, ex=self.__expiration_time)
        self.__redis.set(self.__make_key(key, 'type'),
                         object_type, ex=self.__expiration_time)

        return True

    def get(self, key) -> Optional[object]:
        object_type = self.__redis.get(self.__make_key(key, 'type'))
        value = self.__redis.get(self.__make_key(key, 'content'))

        # return values from redis are binary
        # We check for value here just in case the value expired between
        # reading the object type and the value
        if object_type == b'obj' and value:
            return pickle.loads(value)

        # This is safe -- if the key has expired, we'll return None here
        return value
