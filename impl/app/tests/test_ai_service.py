import json
import os
import time
import pytest
import faker

from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.util.sparql_formatter import SparqlFormatter
from src.util.fs import FS

# pytest -v tests/test_ai_service.py


def test_constructor():
    ai_svc = AiService()
    assert ai_svc.aoai_endpoint.startswith("https://")
    assert ai_svc.aoai_endpoint.endswith(".openai.azure.com/")
    assert ai_svc.aoai_version.startswith("202")
    assert ai_svc.aoai_client is not None

def test_generate_sparql_from_user_prompt():
    ai_svc = AiService()
    owl = FS.read("ontologies/libraries.owl")
    assert owl != None
    assert len(owl) > 1000
    assert len(owl) < 10000
    obj = dict()
    obj["session_id"] = ""
    obj["completion_id"] = ""
    obj["completion_model"] = ""
    obj["prompt_tokens"] = -1
    obj["completion_tokens"] = -1
    obj["total_tokens"] = -1
    obj["sparql"] = ""
    obj["error"] = ""
    obj["natural_language"] = (
        "What are the dependencies of the pypi type of library named flask ?"
    )
    obj["owl"] = owl

    result_obj = ai_svc.generate_sparql_from_user_prompt(obj)
    print(result_obj)
    FS.write_json(result_obj, "tmp/test_generate_sparql_from_user_prompt.json")
    assert result_obj["prompt_tokens"] > 1000
    assert result_obj["prompt_tokens"] < 2000
    assert result_obj["completion_tokens"] > 30
    assert result_obj["completion_tokens"] < 130
    assert result_obj["total_tokens"] > 1000
    assert result_obj["total_tokens"] < 2000
    assert result_obj["elapsed"] > 0.001

    sf = SparqlFormatter()
    sparql = result_obj["sparql"]
    pretty = SparqlFormatter().pretty(sparql)
    assert 'http://cosmosdb.com/caig#' in pretty
    print(pretty)

def test_generate_embeddings():
    ai_svc = AiService()
    resp = ai_svc.generate_embeddings("python fastapi pydantic microservices")
    print(resp)
    assert resp is not None
    assert "CreateEmbeddingResponse" in str(type(resp))
    assert len(resp.data[0].embedding) == 1536

