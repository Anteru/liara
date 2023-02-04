from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Optional
import abc
import hashlib
import logging
import os
import pathlib
import pickle
import sqlite3


@dataclass
class CacheInfo:
    """Information about a cache. Note that the information can be approximated
    as getting the exact numbers may be costly."""

    size: int = 0
    """Approximate number of objects stored in the cache."""

    entry_count: int = 0
    """Approximate number of objects stored in the cache."""

    name: str = ""
    """A human-friendly name for this cache."""


class Cache(abc.ABC):
    """Interface for key-value caches.
    """
    @abc.abstractmethod
    def put(self, key: bytes, value: object) -> bool:
        """Put a value into the cache using the provided key.

        :param key: The key under which ``value`` will be stored.
        :param value: A pickable Python object to be stored.
        :return: ``True`` if the value was added to the cache, ``False`` if
                 it was already cached.
        """

    @abc.abstractmethod
    def get(self, key: bytes) -> Optional[object]:
        """Get a stored object.

        :param key: The object key.
        :return: An object if one exists. Otherwise, return ``None``.
        """

    def persist(self) -> None:
        """Persists this cache to disk/persistent storage.

        This function should be called after the cache has been populated. On
        the next run, the constructor will then pick up the index and return
        cached data.
        """
        return None

    @abc.abstractmethod
    def clear(self) -> None:
        """Clear the contents of the cache.

        .. versionadded:: 2.5
        """

    @abc.abstractmethod
    def inspect(self) -> CacheInfo:
        """Get an overview of the cached data.

        .. versionadded:: 2.5"""


class FilesystemCache(Cache):
    """A :py:class:`Cache` implementation which uses the filesystem to cache
    data.

    This cache tries to load a previously generated index. Use
    :py:meth:`persist` to write the cache index to disk.
    """
    __index: Dict[bytes, pathlib.Path]

    __log = logging.getLogger(f'{__name__}.{__qualname__}')

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

    def clear(self) -> None:
        import shutil
        self.__log.debug('Clearing cache')
        self.__index = {}
        shutil.rmtree(self.__path, ignore_errors=True)
        os.makedirs(self.__path, exist_ok=True)

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

    def inspect(self):
        count = len(self.__index)

        size = 0
        for path in self.__index.values():
            size += pathlib.Path(path).stat().st_size

        return CacheInfo(size, count, 'Filesystem')


class Sqlite3Cache(Cache):
    """A :py:class:`Cache` implementation which uses SQLite to store the data.
    This is mostly useful if creating many files is slow, for instance due to
    anti-virus software.

    This cache tries to load a previously generated index. Use
    :py:meth:`persist` to write the cache index to disk.
    """

    __log = logging.getLogger(f'{__name__}.{__qualname__}')

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

    def clear(self) -> None:
        self.__log.debug('Clearing cache')
        self.__cursor.execute("DELETE FROM cache;")
        self.__connection.commit()
        self.__cursor.execute("VACUUM;")

    def persist(self):
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

    def inspect(self):
        size, count = self.__cursor.execute(
            'SELECT SUM(LENGTH(data)), COUNT(*) FROM cache;'
        ).fetchone()

        # If there is no data stored, the query above will return None, None
        if size is None:
            size = 0

        if count is None:
            count = 0

        return CacheInfo(size, count, 'Sqlite3')


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

        self.__index[key] = value
        return True

    def get(self, key: bytes) -> Optional[object]:
        return self.__index.get(key, None)

    def clear(self):
        self.__index = {}

    def inspect(self):
        import sys
        size = sys.getsizeof(self.__index)

        size += sum([sys.getsizeof(k) + sys.getsizeof(v)
                     for k, v in self.__index.value()])

        count = len(self.__index)

        return CacheInfo(size, count, 'In-Memory')


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

        pipeline = self.__redis.pipeline()
        pipeline.set(self.__make_key(key, 'content'),
                     value, ex=self.__expiration_time)
        pipeline.set(self.__make_key(key, 'type'),
                     object_type, ex=self.__expiration_time)

        return all(pipeline.execute())

    def get(self, key) -> Optional[object]:
        pipeline = self.__redis.pipeline()

        pipeline.get(self.__make_key(key, 'type'))
        pipeline.get(self.__make_key(key, 'content'))

        object_type, value = pipeline.execute()

        # Can't continue if any of those is None: Without the type we don't
        # know what to decode, and without a value the result is None anyways
        if object_type is None or value is None:
            return None

        if object_type == b'obj':
            return pickle.loads(value)

        return value

    def clear(self):
        for key in self.__redis.scan_iter('liara/*'):
            self.__redis.delete(key)

    def inspect(self):
        return CacheInfo(name='Redis')


class NullCache(Cache):
    """The null cache drops all requests and does not cache any data.

    This is mostly useful to disable caching in APIs which require a cache
    instance.
    """
    def put(self, key: bytes, value: object) -> bool:
        return True

    def get(self, key: bytes) -> Optional[object]:
        return None

    def clear(self) -> None:
        pass

    def inspect(self) -> CacheInfo:
        return CacheInfo(0, 0, 'Null')
