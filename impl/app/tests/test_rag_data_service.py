import json
import pytest

from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.services.cosmos_vcore_service import CosmosVCoreService
from src.services.config_service import ConfigService
from src.services.rag_data_service import RAGDataService
from src.services.strategy_builder import StrategyBuilder
from src.services.rag_data_result import RAGDataResult
from src.util.fs import FS

# pytest -v tests/test_rag_data_service.py
# del tmp/*.* ; pytest tests/test_rag_data_service.py

@pytest.mark.asyncio
async def test_get_database_rag_data():
    ConfigService.set_standard_unit_test_env_vars()
    opts = dict()
    opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
    ai_svc = AiService()
    vcore = CosmosVCoreService(opts)
    rds = RAGDataService(ai_svc, vcore)

    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)
    user_text = "lookup PyPi Flask"
    strategy_obj = await sb.determine(user_text)
    assert strategy_obj["strategy"] == "db"

    rdr: RAGDataResult = await rds.get_rag_data(user_text, 7)
    FS.write_json(rdr.get_data(), "tmp/test_get_database_rag_data.json")
    text = rdr.as_system_prompt_text()
    FS.write("tmp/test_get_database_rag_system_prompt.txt", text)

    assert rdr.get_strategy() == "db"
    assert rdr.get_data()["entitytype"] == "pypi"
    assert rdr.get_data()["name"] == "flask"
    assert rdr.get_query() == "{'libtype': 'pypi', 'name': 'flask'}"
    assert len(rdr.get_rag_docs()) > 0

@pytest.mark.asyncio
async def test_get_vector_rag_data():
    ConfigService.set_standard_unit_test_env_vars()
    opts = dict()
    opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
    ai_svc = AiService()
    vcore = CosmosVCoreService(opts)
    rds = RAGDataService(ai_svc, vcore)

    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)
    user_text = "what is the purpose of the Python pydantic library"
    strategy_obj = await sb.determine(user_text)
    assert strategy_obj["strategy"] == "vector"

    rdr: RAGDataResult = await rds.get_rag_data(user_text, 5)
    FS.write_json(rdr.get_data(), "tmp/test_get_vector_rag_data.json")
    text = rdr.as_system_prompt_text()
    FS.write("tmp/test_get_vector_rag_system_prompt.txt", text)
    assert len(rdr.get_rag_docs()) > 0

@pytest.mark.asyncio
async def test_get_graph_rag_data():
    ConfigService.set_standard_unit_test_env_vars()
    opts = dict()
    opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
    ai_svc = AiService()
    vcore = CosmosVCoreService(opts)
    rds = RAGDataService(ai_svc, vcore)
    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)
    user_text = "What are the dependencies of the pypi type of library named flask ?"
    strategy_obj = await sb.determine(user_text)
    assert strategy_obj["strategy"] == "graph"

    rdr: RAGDataResult = await rds.get_rag_data(user_text,5)
    FS.write_json(rdr.get_data(),"tmp/test_get_graph_rag_data.json")
    text = rdr.as_system_prompt_text()
    FS.write("tmp/test_get_graph_rag_system_prompt.txt", text)
    assert len(rdr.get_rag_docs()) > 0
