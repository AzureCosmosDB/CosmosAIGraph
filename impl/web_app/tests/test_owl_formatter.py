import json
import os
import time
import pytest

from src.util.owl_formatter import OwlFormatter

# pytest -v tests/test_owl_formatter.py


def test_minimize():
    of = OwlFormatter()
    owl = sample_owl()
    minimized = of.minimize(owl)
    print("---")
    print(minimized)
    print("---")
    assert len(owl) > 4000
    assert len(minimized) < 3750
    assert minimized.startswith(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rdf:RDF xmlns="http://cosmosdb.com/caig#"'
    )
    assert minimized.endswith("</owl:DatatypeProperty></rdf:RDF>")


def sample_owl():
    return """
<?xml version="1.0"?>

<rdf:RDF
  xmlns      = "http://cosmosdb.com/caig#"
  xmlns:owl  = "http://www.w3.org/2002/07/owl#"
  xmlns:rdf  = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:rdfs = "http://www.w3.org/2000/01/rdf-schema#"
  xmlns:xsd  = "http://www.w3.org/2001/XMLSchema#">

  <owl:Ontology rdf:about="">
    <rdfs:comment>
      A custom ontology for the NPM and PyPi Libraries reference graph
    </rdfs:comment>
    <rdfs:label>Software Libraries Ontology</rdfs:label>
  </owl:Ontology>

  <owl:Class rdf:ID="Lib">
    <rdfs:label xml:lang="en">Lib</rdfs:label>
    <rdfs:comment xml:lang="en">A software library or package, such as from NPM or PyPi</rdfs:comment>
  </owl:Class>

  <owl:Class rdf:ID="Dev">
    <rdfs:label xml:lang="en">Dev</rdfs:label>
    <rdfs:comment xml:lang="en">A software Developer of a library</rdfs:comment>
  </owl:Class>

  <owl:Class rdf:ID="Doc">
    <rdfs:label xml:lang="en">Doc</rdfs:label>
    <rdfs:comment xml:lang="en">A documentation page related to a library</rdfs:comment>
  </owl:Class>

  <owl:ObjectProperty rdf:ID="uses_lib">
	<rdfs:label xml:lang="en">uses_lib</rdfs:label>
	<rdfs:comment xml:lang="en">Library uses another Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range  rdf:resource="#Lib" />
  </owl:ObjectProperty>

  <owl:ObjectProperty rdf:ID="used_by_lib">
	<rdfs:label xml:lang="en">used_by_lib</rdfs:label>
	<rdfs:comment xml:lang="en">Library is used by another Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range  rdf:resource="#Lib" />
  </owl:ObjectProperty>

  <owl:ObjectProperty rdf:ID="developer_of">
	<rdfs:label xml:lang="en">developer_of</rdfs:label>
	<rdfs:comment xml:lang="en">Developer is the creator/author/maintainer of a Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Dev" />
    <rdfs:range  rdf:resource="#Lib" />
  </owl:ObjectProperty>

  <owl:ObjectProperty rdf:ID="developed_by">
	<rdfs:label xml:lang="en">developed_by</rdfs:label>
	<rdfs:comment xml:lang="en">Library is created/authored/maintained by a Developer</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range  rdf:resource="#Dev" />
  </owl:ObjectProperty>

  <owl:DatatypeProperty rdf:ID="ln">
    <rdfs:label xml:lang="en">ln</rdfs:label>
    <rdfs:comment xml:lang="en">The name of a Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string" />
  </owl:DatatypeProperty>

  <owl:DatatypeProperty rdf:ID="lt">
    <rdfs:label xml:lang="en">lt</rdfs:label>
    <rdfs:comment xml:lang="en">The type of a Library (i.e. - pypi)</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string" />
  </owl:DatatypeProperty>

  <owl:DatatypeProperty rdf:ID="lic">
    <rdfs:label xml:lang="en">lic</rdfs:label>
    <rdfs:comment xml:lang="en">The License associated with a Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string" />
  </owl:DatatypeProperty>

  <owl:DatatypeProperty rdf:ID="kwds">
    <rdfs:label xml:lang="en">kwds</rdfs:label>
    <rdfs:comment xml:lang="en">The list of Keywords associated with a Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string" />
  </owl:DatatypeProperty>

  <owl:DatatypeProperty rdf:ID="desc">
    <rdfs:label xml:lang="en">desc</rdfs:label>
    <rdfs:comment xml:lang="en">The description of a Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string" />
  </owl:DatatypeProperty>

  <owl:DatatypeProperty rdf:ID="latestReleaseYear">
    <rdfs:label xml:lang="en">latestReleaseYear</rdfs:label>
    <rdfs:comment xml:lang="en">The year of the latest release of the Library</rdfs:comment>
    <rdfs:domain rdf:resource="#Lib" />
    <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#int" />
  </owl:DatatypeProperty>

</rdf:RDF>
""".strip()
