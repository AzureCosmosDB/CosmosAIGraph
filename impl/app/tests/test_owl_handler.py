import os
import pytest

from xml.sax import make_parser

from src.services.config_service import ConfigService
from src.util.fs import FS
from src.util.owl_sax_handler import OwlSaxHandler

# pytest -v tests/test_owl_handler.py

def test_owl_sax_handler():
    owl_filename = "ontologies/libraries.owl"
    parser = make_parser()
    handler = OwlSaxHandler()
    parser.setContentHandler(handler)
    parser.parse(owl_filename)
    FS.write_json(handler.get_data(), "tmp/test_owl_sax_handler.json")

    data = handler.get_data()
    classes = data["classes"]
    object_properties = data["object_properties"]
    datatype_properties = data["datatype_properties"]

    assert classes == ["Dev", "Doc", "Lib"]

    print(sorted(object_properties.keys()))
    print(sorted(datatype_properties.keys()))

    assert sorted(object_properties.keys()) == ['developed_by', 'developer_of', 'used_by_lib', 'uses_lib']
    assert sorted(datatype_properties.keys()) == ['desc', 'kwds', 'latestReleaseYear', 'lic', 'ln', 'lt']

    assert object_properties["developed_by"]["name"] == "developed_by"
    assert object_properties["developed_by"]["domain"] == ["Lib"]
    assert object_properties["developed_by"]["range"] == ["Dev"]

    assert datatype_properties["latestReleaseYear"]["name"] == "latestReleaseYear"
    assert datatype_properties["latestReleaseYear"]["domain"] == ["Lib"]
    assert datatype_properties["latestReleaseYear"]["range"] == ["http://www.w3.org/2001/XMLSchemaint"]

