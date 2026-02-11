# SPDX-FileCopyrightText: 2022 Matthäus G. Chajdas <dev@anteru.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

from liara.cache import MemoryCache


def test_put_retrieve_memory_cache():
    c = MemoryCache()
    key = bytes(1)
    c.put(key, 23)
    assert c.get(key) == 23


def test_memory_cache_inspect():
    import sys

    c = MemoryCache()
    key = bytes(1)
    value = bytes([1, 2, 3, 4])

    c.put(key, value)
    ci = c.inspect()
    assert ci.entry_count == 1
    assert ci.size >= sys.getsizeof(value)
