from liara.cache import MemoryCache


def test_put_retrieve_memory_cache():
    c = MemoryCache()
    c.put(1, 23)
    assert c.get(1) == 23
