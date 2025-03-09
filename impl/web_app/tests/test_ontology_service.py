import pytest

from src.services.config_service import ConfigService
from src.services.ontology_service import OntologyService

# pytest -v tests/test_ontology_service.py


@pytest.mark.asyncio
async def test_get_owl_content():
    ConfigService.set_standard_unit_test_env_vars()
    assert "ontologies/libraries.owl" == ConfigService.graph_source_owl_filename()
    assert (
        "http://127.0.0.1:8001/ontology" == ConfigService.graph_service_ontology_url()
    )

    await OntologyService.initialize()

    owl = OntologyService.get_owl_content().strip()

    assert "ontologies/libraries.owl" == OntologyService.owl_filename
    assert "http://127.0.0.1:8001/ontology" == OntologyService.http_url
    assert 200 == OntologyService.http_status_code
    assert True == OntologyService.http_content_saved

    assert str(type(owl)) == "<class 'str'>"
    assert owl.startswith('<?xml version="1.0"?>')
    assert owl.endswith("</rdf:RDF>")
    assert '<rdfs:label xml:lang="en">Library</rdfs:label>' in owl
    assert '<owl:ObjectProperty rdf:ID="uses_library">' in owl
    assert '<owl:ObjectProperty rdf:ID="used_by_library">' in owl
