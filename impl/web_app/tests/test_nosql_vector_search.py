import json
import os
import time
import uuid
import pytest

from src.services.ai_conversation import AiConversation
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.util.fs import FS

# pytest -v tests/test_nosql_vector_search.py


def test_flask_embedding():
    # This method simply tests this test method: embedding_for_library(libname)
    embedding = embedding_for_library("flask")
    assert len(embedding) == 1536
    assert embedding[0] == -0.00011316168092889711
    assert embedding[-1] == -0.054162509739398956


def test_sql():
    nosql_svc = CosmosNoSQLService()  # non need to initialize in this test
    embedding_value = [-0.1, -0.2, -0.3]
    embedding_attr = "embedding"
    limit = 4
    sql = nosql_svc.vector_search_sql(embedding_value, embedding_attr, limit)
    print(sql)
    FS.write_lines([sql], "tmp/sql.txt")
    assert (
        sql
        == "SELECT TOP 4 c, VectorDistance(c.embedding, [-0.1, -0.2, -0.3]) AS score FROM c ORDER BY VectorDistance(c.embedding, [-0.1, -0.2, -0.3])"
    )


# @pytest.mark.skip(reason="This test is currently disabled.")
@pytest.mark.asyncio
async def test_vector_search():
    ConfigService.set_standard_unit_test_env_vars()
    os.environ["CAIG_GRAPH_SOURCE_TYPE"] = "cosmos_nosql"
    os.environ["CAIG_GRAPH_SOURCE_DB"] = "caig"
    nosql_svc = None
    try:
        assert ConfigService.graph_source() == "cosmos_nosql"
        assert ConfigService.graph_source_db() == "caig"
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        nosql_svc.set_container(ConfigService.graph_source_container())

        # a vector search with the flask embedding is expected to return flask
        # as the first search result with a score approaching 1.0
        for libname in "flask,pydantic,m26".split(","):
            embedding = embedding_for_library(libname)
            docs = await nosql_svc.vector_search(embedding, "embedding", 4)
            FS.write_json(docs, "tmp/vector_search_results_{}.txt".format(libname))
            assert len(docs) == 4
            doc = docs[0]
            assert doc["c"]["name"] == libname
            assert doc["score"] > 0.999
            assert doc["score"] < 1.001
    finally:
        if nosql_svc != None:
            await nosql_svc.close()


def embedding_for_library(libname):
    infile = "../../data/pypi/wrangled_libs/{}.json".format(libname).lower()
    doc = FS.read_json(infile)
    return doc["embedding"]
