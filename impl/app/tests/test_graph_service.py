import json
import pytest

from src.services.graph_service import GraphService
from src.util.sparql_template import SparqlTemplate
from src.services.config_service import ConfigService
from src.util.fs import FS

# pytest -v tests/test_graph_service.py

@pytest.mark.asyncio
async def test_init_and_query():
    ConfigService.set_standard_unit_test_env_vars()
    expected_triples_count = 4372
    gs = GraphService()
    await gs.initialize()
    count = 0
    assert str(type(gs.graph)) == "<class 'rdflib.graph.Graph'>"
    for s, p, o in gs.graph:
        count = count + 1
    assert count == expected_triples_count

    liveness_data = gs.liveness_check()
    assert liveness_data["alive"] == True
    assert liveness_data["rows_read"] > 80
    assert liveness_data["epoch"] > 1707296702
    assert liveness_data["epoch"] < 2707296702

    q = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10"
    rqr = gs.query(q)  # query() method returns a RdfQueryResult
    rqr.prune_data()
    rdata = rqr.get_data()
    FS.write("tmp/test_graph_service_q1.json", json.dumps(rdata, indent=2))
    assert rdata["sparql"] == q
    assert rdata["row_count"] == 10
    assert len(rdata["results"]) == 10
    assert len(rqr.get_results()) == 10

    assert rqr.has_exception() == False
    assert rqr.get_exception() == None
    rqr.set_exception("test exception")
    assert rqr.has_exception() == True
    assert rqr.get_exception() == "test exception"

    q = "SELECT (COUNT(*) as ?TriplesCount) WHERE { ?s ?p ?o }"
    rqr = gs.query(q)  # query() method returns a RdfQueryResult
    rdata = rqr.get_data()
    FS.write("tmp/test_graph_service_q2.json", json.dumps(rdata, indent=2))
    assert rdata["sparql"] == q
    assert rdata["row_count"] == 1
    assert len(rdata["results"]) == 1
    assert rdata["results"][0]["TriplesCount"] == str(expected_triples_count)

    # This tests the use of class SparqlTemplate
    values = dict()
    values["id"] = "pypi_m26"
    values["limit"] = "100"
    q = SparqlTemplate().render("developers_of_library.txt", values)
    rqr = gs.query(q)  # query() method returns a RdfQueryResult
    rdata = rqr.get_data()
    FS.write("tmp/test_graph_service_q3.json", json.dumps(rdata, indent=2))
    assert rdata["row_count"] == 2
    assert len(rdata["results"]) == 2
    agg_developers = dict()
    for result in rdata["results"]:
        dev = result["o"]
        agg_developers[dev] = 0
    sorted_developers = sorted(agg_developers.keys())
    expected_developers = [
        "http://cosmosdb.com/caig/christopher.joakim@gmail.com",
        "http://cosmosdb.com/caig/christopher_joakim",
    ]
    assert sorted_developers == expected_developers

    # This tests a BOM traversal of a lib that doesn't exist
    if True:
        bqr = gs.bom_query("pypi", "not_there", 21)
        rdata = bqr.get_data()
        FS.write(
            "tmp/test_graph_service_bom_not_there.json", json.dumps(rdata, indent=2)
        )
        assert rdata["libname"] == "not_there"
        assert rdata["libtype"] == "pypi"
        assert rdata["max_depth"] == 21
        assert rdata["actual_depth"] == 1
        assert rdata["exception"] == None
        assert bqr.get_lib_count() == 1

        # test the execption methods
        assert bqr.has_exception() == False
        assert bqr.is_unvisited("spring_boot") == True
        bqr.set_exception("test exception")
        assert bqr.has_exception() == True
        assert bqr.get_exception() == "test exception"

    # This tests a BOM traversal of a lib that does exist
    if True:
        bqr = gs.bom_query("pypi", "requests", 99)
        rdata = bqr.get_data()
        FS.write(
            "tmp/test_graph_service_bom_requests.json", json.dumps(rdata, indent=2)
        )
        assert rdata["libname"] == "requests"
        assert rdata["libtype"] == "pypi"
        assert rdata["max_depth"] == 99
        assert rdata["actual_depth"] == 5
        assert rdata["exception"] == None
        assert bqr.get_lib_count() == 13

        expected_pypi_requests_dependencies = [
            "pypi_idna",
            "pypi_pysocks",
            "pypi_charset_normalizer",
            "pypi_urllib3",
            "pypi_chardet",
            "pypi_certifi",
        ]
        expected_pypi_urllib3_dependencies = [
            "pypi_zstandard",
            "pypi_pysocks!",
            "pypi_brotli",
            "pypi_brotlicffi",
        ]
        assert (
            bqr.get_bom_lib_by_key("pypi_requests")
            == expected_pypi_requests_dependencies
        )
        assert (
            bqr.get_bom_lib_by_key("pypi_urllib3") == expected_pypi_urllib3_dependencies
        )


@pytest.mark.asyncio
async def test_owl():
    ConfigService.set_standard_unit_test_env_vars()
    gs = GraphService()
    await gs.initialize()
    owl_info = gs.owl_info()
    assert owl_info["ontology_file"].endswith(".owl")
    assert owl_info["owl"].startswith('<?xml version="1.0"?>')
    assert owl_info["error"] == None


@pytest.mark.asyncio
async def test_deep_bom_query():
    ConfigService.set_standard_unit_test_env_vars()
    gs = GraphService()
    await gs.initialize()
    bqr = gs.bom_query(
        "pypi", "requests", 99
    )  # query method returns a BomQueryResult object
    rdata = bqr.get_data()
    FS.write("tmp/test_graph_service_deep_bom_query.json", json.dumps(rdata, indent=2))
    assert bqr.get_actual_depth() == 5  # 5 levels is deep given the mini test dataset
    assert (
        len(bqr.get_bom_libs().keys()) == 13
    )  # 5 levels is deep given the mini test dataset
