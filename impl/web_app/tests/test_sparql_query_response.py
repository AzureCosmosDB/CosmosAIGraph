import json
import os
import time
import pytest

from difflib import *

from src.util.fs import FS
from src.util.sparql_query_response import SparqlQueryResponse

# pytest -v tests/test_sparql_query_response.py


class SimulatedHttpxResponse:
    # This class simulates a httpx.Response
    def __init__(self, text):
        self.text = text


def test_null_http_response():
    sqr = SparqlQueryResponse(None)
    sqr.parse()
    assert sqr.parse_error == True
    assert sqr.has_errors() == True


def test_triples_query():
    r = simulated_response("samples/sample_post_sparql_triples_query.json")
    # print("r.text: {}".format(r.text))
    sqr = SparqlQueryResponse(r)
    sqr.parse()

    assert len(r.text) > 100
    assert r.text == sqr.text
    assert sqr.parse_error == False
    assert sqr.response_obj != None
    assert sqr.elapsedMs() == 1.0

    # Verify that the outermost response_obj dict has the expected keys:
    expected_keys = [
        "sparql",
        "results",
        "elapsed",
        "row_count",
        "error",
        "start_time",
        "finish_time",
    ]
    print(sqr.response_obj.keys())
    for key in expected_keys:
        assert key in sqr.response_obj.keys()

    # Verify the inner query results
    assert str(type(sqr.query_results_obj)) == "<class 'dict'>"
    assert sqr.result_variables() == ["s", "p", "o"]

    results_bindings = sqr.results_bindings()
    assert len(results_bindings) == 3

    svalues = sqr.binding_values_for(["s"])
    ovalues = sqr.binding_values_for(["o"])
    bvalues = sqr.binding_values()
    FS.write_json(svalues, "tmp/tsvalues.json")
    FS.write_json(ovalues, "tmp/tovalues.json")
    FS.write_json(bvalues, "tmp/tbvalues.json")

    assert svalues == [
        {"s": "http://cosmosdb.com/caig#mattermostwrapper"},
        {"s": "http://cosmosdb.com/caig#mattermostwrapper"},
        {"s": "http://cosmosdb.com/caig#mattermostwrapper"},
    ]

    assert ovalues == [
        {"o": "http://cosmosdb.com/caig#rasa"},
        {"o": "http://cosmosdb.com/caig#btotharye@gmail.com"},
        {"o": "http://cosmosdb.com/caig#brian_hopkins"},
    ]

    assert bvalues == [
        {
            "s": "http://cosmosdb.com/caig#mattermostwrapper",
            "p": "http://cosmosdb.com/caig#used_by_library",
            "o": "http://cosmosdb.com/caig#rasa",
        },
        {
            "s": "http://cosmosdb.com/caig#mattermostwrapper",
            "p": "http://cosmosdb.com/caig#developed_by",
            "o": "http://cosmosdb.com/caig#btotharye@gmail.com",
        },
        {
            "s": "http://cosmosdb.com/caig#mattermostwrapper",
            "p": "http://cosmosdb.com/caig#developed_by",
            "o": "http://cosmosdb.com/caig#brian_hopkins",
        },
    ]


def test_flask_query():
    r = simulated_response("samples/sample_post_sparql_flask_query.json")
    # print("r.text: {}".format(r.text))
    sqr = SparqlQueryResponse(r)
    sqr.parse()

    assert len(r.text) > 100
    assert r.text == sqr.text
    assert sqr.parse_error == False
    assert sqr.response_obj != None
    assert sqr.elapsedMs() == 1.0

    # Verify that the outermost response_obj dict has the expected keys:
    expected_keys = [
        "sparql",
        "results",
        "elapsed",
        "row_count",
        "error",
        "start_time",
        "finish_time",
    ]
    print(sqr.response_obj.keys())
    for key in expected_keys:
        assert key in sqr.response_obj.keys()

    # Verify the inner query results
    assert str(type(sqr.query_results_obj)) == "<class 'dict'>"
    assert sqr.result_variables() == ["used_library"]

    results_bindings = sqr.results_bindings()
    assert len(results_bindings) == 6

    ulvalues = sqr.binding_values_for(["used_library"])
    novalues = sqr.binding_values_for(["typ0_error"])
    bvalues = sqr.binding_values()
    FS.write_json(ulvalues, "tmp/fulvalues.json")
    FS.write_json(novalues, "tmp/fnovalues.json")
    FS.write_json(bvalues, "tmp/fbvalues.json")

    assert novalues == []

    assert ulvalues == [
        {"used_library": "http://cosmosdb.com/caig#blinker"},
        {"used_library": "http://cosmosdb.com/caig#werkzeug"},
        {"used_library": "http://cosmosdb.com/caig#click"},
        {"used_library": "http://cosmosdb.com/caig#asgiref"},
        {"used_library": "http://cosmosdb.com/caig#jinja2"},
        {"used_library": "http://cosmosdb.com/caig#itsdangerous"},
    ]

    assert bvalues == [
        {"used_library": "http://cosmosdb.com/caig#blinker"},
        {"used_library": "http://cosmosdb.com/caig#werkzeug"},
        {"used_library": "http://cosmosdb.com/caig#click"},
        {"used_library": "http://cosmosdb.com/caig#asgiref"},
        {"used_library": "http://cosmosdb.com/caig#jinja2"},
        {"used_library": "http://cosmosdb.com/caig#itsdangerous"},
    ]


def simulated_response(infile):
    obj = FS.read_json(infile)
    r = SimulatedHttpxResponse(json.dumps(obj))
    return r
