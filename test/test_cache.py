from liara.cache import MemoryCache
import pytest

def test_put_retrieve_memory_cache():
    c = MemoryCache()
    c.put(1, 23)
    assert c.get(1) == 23