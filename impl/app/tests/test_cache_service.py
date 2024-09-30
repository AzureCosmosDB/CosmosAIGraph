import json
import os
import time
import pytest

from src.services.cache_service import CacheService
from src.services.config_service import ConfigService


def test_constructor_clear_set_get():
    opts = dict()
    opts["container"] = "test_cache"
    opts["environment"] = "unit_testing"
    cache_svc = CacheService(opts)

    print("dbname: {}".format(cache_svc.dbname))
    print("cname:  {}".format(cache_svc.cname))
    print("conn_string: {}".format(cache_svc.conn_string))
    assert cache_svc.dbname == ConfigService.graph_source_db()
    assert cache_svc.cname == "test_cache"

    # test the is_key_value_valid() method while we're at it
    assert cache_svc.is_key_value_valid(None) == False
    assert cache_svc.is_key_value_valid("") == False
    assert cache_svc.is_key_value_valid("pypi_flask_3") == True

    cache_svc.clear()
    assert cache_svc.count_docs() == 0

    epoch = str(int(time.time()))
    key1 = "key_{}_1".format(epoch)
    key2 = "key_{}_2".format(epoch)

    cached = cache_svc.get(key1)
    assert cached == None

    # set the cache key
    doc = dict()
    doc["name"] = "anything"
    doc["version"] = 1
    res = cache_svc.set(key1, doc)
    print("res1: {}".format(res))
    count = cache_svc.count_docs()
    print("count: {}".format(count))
    assert count == 1

    # set the same cache key again, with an updated doc
    doc["version"] = 2
    res = cache_svc.set(key1, doc)
    print("res2: {}".format(res))
    count = cache_svc.count_docs()
    print("count: {}".format(count))
    assert count == 1

    # get the cache key
    cached = cache_svc.get(key1)
    print(str(type(cached)))
    if "_id" in cached.keys():
        del cached["_id"]  # remove the _id field for json serialization
    print(json.dumps(cached, indent=2))
    assert cached is not None
    count = cache_svc.count_docs()
    print("count: {}".format(count))
    assert count == 1
    assert cached["version"] == 2

    # set a different cache key
    doc = dict()
    doc["name"] = "something"
    doc["version"] = 42
    res = cache_svc.set(key2, doc)
    count = cache_svc.count_docs()
    print("count3: {}".format(count))
    assert count == 2
