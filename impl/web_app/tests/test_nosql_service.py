import json
import os
import time
import uuid
import pytest

from src.services.ai_conversation import AiConversation
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.util.fs import FS

# pytest -v tests/test_nosql_service.py
# # @pytest.mark.skip(reason="This test is currently disabled.")


def initialize_conversation(user_msg):
    conv = AiConversation()
    conv.add_user_message(user_msg)
    conv.add_system_message(
        "CAIG_GRAPH_SOURCE_TYPE is: {} at {}".format(
            ConfigService.graph_source(), ConfigService.epoch()
        )
    )
    return conv


@pytest.mark.asyncio
async def test_save_load_conversation():
    ConfigService.set_standard_unit_test_env_vars()
    os.environ["CAIG_GRAPH_SOURCE_TYPE"] = "cosmos_nosql"
    os.environ["CAIG_GRAPH_SOURCE_DB"] = "caig"

    nosql_svc = None
    try:
        assert ConfigService.graph_source() == "cosmos_nosql"
        assert ConfigService.graph_source_db() == "caig"
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        msg = "pytest cosmos_nosql {}".format(time.time())
        conv1: AiConversation = initialize_conversation(msg)
        print(conv1.serialize())
        await nosql_svc.save_conversation(conv1)
        conv_id = conv1.get_conversation_id()

        conv2: AiConversation = await nosql_svc.load_conversation(conv_id)
        assert conv1.get_conversation_id() == conv2.get_conversation_id()
        assert conv1.get_created_at() == conv2.get_created_at()

        FS.write_json(conv2.get_data(), "tmp/test_save_load_conversation.json")
    finally:
        if nosql_svc != None:
            await nosql_svc.close()


@pytest.mark.asyncio
async def test_find_library():
    ConfigService.set_standard_unit_test_env_vars()
    os.environ["CAIG_GRAPH_SOURCE_TYPE"] = "cosmos_nosql"
    os.environ["CAIG_GRAPH_SOURCE_DB"] = "caig"
    nosql_svc = None
    try:
        assert ConfigService.graph_source() == "cosmos_nosql"
        assert ConfigService.graph_source_db() == "caig"
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        doc = await nosql_svc.find_library("flask")
        assert doc["name"] == "flask"
        assert doc["libtype"] == "pypi"
    finally:
        if nosql_svc != None:
            await nosql_svc.close()


@pytest.mark.asyncio
async def test_get_documents_by_and_names():
    ConfigService.set_standard_unit_test_env_vars()
    os.environ["CAIG_GRAPH_SOURCE_TYPE"] = "cosmos_nosql"
    os.environ["CAIG_GRAPH_SOURCE_DB"] = "caig"
    nosql_svc = None
    try:
        assert ConfigService.graph_source() == "cosmos_nosql"
        assert ConfigService.graph_source_db() == "caig"
        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        names = "flask,pydantic,m26,DoesNotExist".split(",")
        assert len(names) == 4
        docs = await nosql_svc.get_documents_by_name(names)
        assert len(docs) == 3
        result_names = dict()
        for doc in docs:
            name = doc["name"]
            result_names[name] = doc
        assert "flask" in result_names.keys()
        assert "pydantic" in result_names.keys()
        assert "m26" in result_names.keys()
    finally:
        if nosql_svc != None:
            await nosql_svc.close()
