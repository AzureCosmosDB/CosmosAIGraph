import pytest

from src.util.sparql_template import SparqlTemplate
from src.services.config_service import ConfigService

# pytest -v tests/test_sparql_template.py


def test_developers_of_library():
    ConfigService.set_standard_unit_test_env_vars()
    values = dict()
    values["id"] = "pypi_swift"
    values["limit"] = 1989
    text = SparqlTemplate().render("developers_of_library.txt", values)
    expected = """
PREFIX c: <http://cosmosdb.com/caig#>
SELECT ?o
WHERE {
    <http://cosmosdb.com/caig/pypi_swift> c:developed_by ?o .
}
LIMIT 1989
""".strip()
    assert line_by_line_diff(text, expected) == "None"

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
