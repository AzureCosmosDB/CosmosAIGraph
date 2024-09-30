import json
import os
import time
import pytest

from difflib import *

from src.util.sparql_formatter import SparqlFormatter

# pytest -v tests/test_sparql_formatter.py


def test_pretty():
    pretty = SparqlFormatter().pretty(sample_generated_sparql()).strip()
    expected = sample_expected_sparql().strip()
    print("--- pretty")
    print(pretty)
    print("--- expected")
    print(expected)

    diff = ndiff(
        pretty.splitlines(keepends=True),
        expected.splitlines(keepends=True))
    print(''.join(diff), end="")

    assert line_by_line_diff(pretty, expected) == "None"

def test_pretty_noinput():
    pretty = SparqlFormatter().pretty(None)
    assert pretty == None

def test_inject_prefix_and_limit():
    pretty = SparqlFormatter().pretty(no_prefix_query())
    assert pretty.startswith(SparqlFormatter().default_prefix())
    assert pretty.endswith(' LIMIT 100')

def sample_generated_sparql():
    return """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> PREFIX : <http://cosmosdb.com/caig#> SELECT ?dependency ?subDependency WHERE { ?lib :ln 'flask' . ?lib :lt 'pypi' . ?lib :uses_lib ?dependency . OPTIONAL { ?dependency :uses_lib ?subDependency . } }
""".strip()

def no_prefix_query():
    return """
SELECT ?dependencyName WHERE {
  ?lib caig:ln 'flask' .
  ?lib caig:lt 'pypi' .
  ?lib caig:uses_lib ?dependency .
  ?dependency caig:ln ?dependencyName .
}
""".strip()

def sample_expected_sparql():
    return """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX : <http://cosmosdb.com/caig#>
SELECT ?dependency ?subDependency
WHERE {
    ?lib :ln 'flask' .
    ?lib :lt 'pypi' .
    ?lib :uses_lib ?dependency .
    OPTIONAL { ?dependency :uses_lib ?subDependency .
}} LIMIT 100""".strip()

def line_by_line_diff(s1, s2):
    """ return the string value 'None' if no differences, else return a diff description. """
    lines1 = s1.strip().split("\n")
    lines2 = s2.strip().split("\n")
    lines1_count = len(lines1)
    lines2_count = len(lines2)
    if lines1_count != lines2_count:
        return "unequal line counts; {} vs {}".format(lines1_count, lines2_count)
    for idx, line1 in enumerate(lines1):
        line2 = lines2[idx]
        s1 = line1.rstrip()
        s2 = line2.rstrip()
        if s1 != s2:
            return "line {} not equal: {}".format(idx+1, s1)
    return 'None'
