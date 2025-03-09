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

    assert sorted(classes) == ["Developer", "Library"]

    print(sorted(object_properties.keys()))
    print(sorted(datatype_properties.keys()))

    print(object_properties.keys())
    expected = sorted(
        [
            "uses_library",
            "used_by_library",
            "developer_of",
            "developed_by",
        ]
    )
    assert sorted(object_properties.keys()) == expected

    print(datatype_properties.keys())
    expected = sorted(["name", "keywords", "description", "release_count"])
    assert sorted(datatype_properties.keys()) == expected

    assert object_properties["developed_by"]["name"] == "developed_by"
    assert object_properties["developed_by"]["domain"] == ["Library"]
    assert object_properties["developed_by"]["range"] == ["Developer"]
