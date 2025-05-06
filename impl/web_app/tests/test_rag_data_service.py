import json
import pytest

from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.services.entities_service import EntitiesService
from src.services.rag_data_service import RAGDataService
from src.services.strategy_builder import StrategyBuilder
from src.services.rag_data_result import RAGDataResult
from src.util.sparql_query_response import SparqlQueryResponse
from src.util.fs import FS

# pytest -v tests/test_rag_data_service.py
# del tmp/*.* ; pytest tests/test_rag_data_service.py


@pytest.mark.asyncio
async def test_get_database_rag_data():
    ConfigService.set_standard_unit_test_env_vars()
    await EntitiesService.initialize()
    ai_svc = AiService()
    await ai_svc.initialize()
    nosql_svc = CosmosNoSQLService()
    await nosql_svc.initialize()
    rds = RAGDataService(ai_svc, nosql_svc)

    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)
    user_text = "look up Flask"
    strategy_obj = sb.determine(user_text)
    assert strategy_obj["strategy"] == "db"

    rdr: RAGDataResult = await rds.get_rag_data(user_text, 7)
    await nosql_svc.close()
    assert rdr.get_context() == "flask"

    FS.write_json(rdr.get_data(), "tmp/test_get_database_context.json")
    text = rdr.as_system_prompt_text()
    FS.write("tmp/test_get_database_rag_system_prompt.txt", text)

    assert rdr.get_strategy() == "db"
    assert rdr.get_data()["name"] == "flask"
    assert len(rdr.get_rag_docs()) > 0


# @pytest.mark.skip(reason="This test is currently disabled.")
@pytest.mark.asyncio
async def test_get_vector_context():
    ConfigService.set_standard_unit_test_env_vars()
    await EntitiesService.initialize()
    ai_svc = AiService()
    await ai_svc.initialize()
    nosql_svc = CosmosNoSQLService()
    await nosql_svc.initialize()

    rds = RAGDataService(ai_svc, nosql_svc)

    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)
    user_text = "what is the purpose of the Python pydantic library"
    strategy_obj = sb.determine(user_text)
    assert strategy_obj["strategy"] == "vector"

    rdr: RAGDataResult = await rds.get_rag_data(user_text, 5)
    await nosql_svc.close()

    FS.write_json(rdr.get_data(), "tmp/test_get_vector_context.json")
    text = rdr.as_system_prompt_text()
    FS.write("tmp/test_get_vector_rag_system_prompt.txt", text)
    assert len(rdr.get_rag_docs()) > 0


@pytest.mark.asyncio
async def test_get_graph_context():
    ConfigService.set_standard_unit_test_env_vars()
    await EntitiesService.initialize()
    ai_svc = AiService()
    await ai_svc.initialize()
    nosql_svc = CosmosNoSQLService()
    await nosql_svc.initialize()
    rds = RAGDataService(ai_svc, nosql_svc)

    sparql_query_url = rds.graph_microsvc_sparql_query_url()
    assert sparql_query_url == "http://127.0.0.1:8001/sparql_query"

    ai_svc = AiService()
    await ai_svc.initialize()
    sb = StrategyBuilder(ai_svc)
    user_text = "What are the dependencies of the library named flask ?"
    strategy_obj = sb.determine(user_text)
    assert strategy_obj["strategy"] == "graph"

    rdr: RAGDataResult = await rds.get_rag_data(user_text, 5)
    await nosql_svc.close()

    FS.write_json(rdr.get_data(), "tmp/test_get_graph_context.json")
    text = rdr.as_system_prompt_text()
    FS.write("tmp/test_get_graph_rag_system_prompt.txt", text)
    assert len(rdr.get_rag_docs()) > 0


@pytest.mark.asyncio
async def test_post_sparql_triples_query():
    ConfigService.set_standard_unit_test_env_vars()
    await EntitiesService.initialize()
    ai_svc, nosql_svc = None, None
    rds = RAGDataService(ai_svc, nosql_svc)
    sparql = "SELECT * WHERE { ?s ?p ?o . } LIMIT 3"
    sqr: SparqlQueryResponse = await rds.post_sparql_to_graph_microsvc(sparql)
    FS.write_json(sqr.response_obj, "tmp/sample_post_sparql_triples_query.json")
    assert len(sqr.binding_values()) == 3


@pytest.mark.asyncio
async def test_post_sparql_flask_query():
    ConfigService.set_standard_unit_test_env_vars()
    await EntitiesService.initialize()
    ai_svc, nosql_svc = None, None
    rds = RAGDataService(ai_svc, nosql_svc)
    sparql = """
PREFIX c: <http://cosmosdb.com/caig#>
SELECT ?used_library 
WHERE {
    <http://cosmosdb.com/caig#flask> c:uses_library ?used_library .
}
LIMIT 6
"""
    sqr: SparqlQueryResponse = await rds.post_sparql_to_graph_microsvc(sparql)
    FS.write_json(sqr.response_obj, "tmp/sample_post_sparql_flask_query.json")
    assert len(sqr.binding_values()) == 6
