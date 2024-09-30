from src.services.config_service import ConfigService
from src.services.ontology_service import OntologyService

# pytest -v tests/test_ontology_service.py

def test_get_owl_content():
    ConfigService.set_standard_unit_test_env_vars()
    os = OntologyService()
    owl = os.get_owl_content().strip()

    assert str(type(owl)) == "<class 'str'>"
    assert owl.startswith("<?xml version=\"1.0\"?>")
    assert owl.endswith("</rdf:RDF>")
    assert ">Lib</rdfs:label" in owl
