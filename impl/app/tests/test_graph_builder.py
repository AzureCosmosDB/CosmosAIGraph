import os
import pytest

from src.services.graph_builder import GraphBuilder
from src.services.config_service import ConfigService

# pytest -v tests/test_graph_builder.py

@pytest.mark.asyncio
async def test_build_with_libraries_mini_nt_and_owl_file():
    ConfigService.set_standard_unit_test_env_vars()
    expected_triples_count = 4372
    gb = GraphBuilder()
    g = await gb.build()
    count = 0
    assert str(type(g)) == "<class 'rdflib.graph.Graph'>"
    for s, p, o in g:
        count = count + 1
    assert count == expected_triples_count
