import os
import pytest

from src.util.template import Template
from src.services.config_service import ConfigService

# pytest -v tests/test_template.py

def test_get_template_and_render():
    ConfigService.set_standard_unit_test_env_vars()

    t = Template.get_template(os.getcwd(), "test_owl.txt")
    assert t != None

    values = dict()
    values["ns"] = "http://cosmosdb.com/caigtest#"
    values["comment"] = "This is a test comment"
    values["label"] = "This is a test label"

    text = Template.render(t, values)
    assert text.strip() == expected_content()

def expected_content():
    return """
<?xml version="1.0"?>

<!-- This is just a jinja2 template for unit-testing purposes. ->

<rdf:RDF xmlns = "http://cosmosdb.com/caigtest##"
  xml:base   = "http://cosmosdb.com/caigtest#"
  xmlns:owl  = "http://www.w3.org/2002/07/owl#"
  xmlns:rdf  = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:rdfs = "http://www.w3.org/2000/01/rdf-schema#"
  xmlns:xsd  = "http://www.w3.org/2001/XMLSchema#">

  <owl:Ontology rdf:about="">
    <rdfs:comment>This is a test comment</rdfs:comment>
    <rdfs:label>This is a test label</rdfs:label>
  </owl:Ontology>

</rdf:RDF>
""".strip()
