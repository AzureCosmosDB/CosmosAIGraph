import logging
import rdflib
from rdflib import Graph, Literal, RDF, URIRef

# This class is used by class GraphBuilder to build the in-memory rdflib graph
# from JSON documents provided to the append_doc_to_graph(...) method.
# The JSON documents will be read from Cosmos DB, or may initially come
# from a JSON file during your initial development.
#
# Note: This class can be generated from your observed input graph JSON data;
# see file pysrc/util/graph_builder_generator.py


class RdflibTriplesBuilder:

    def __init__(self, attributes_root=None):
        self.attributes_root = attributes_root

    def append_doc_to_graph(self, g, doc, CNS, ns=None):
        """
        This method is called by GraphBuilder.  Each passed JSON document
        may result in zero to many triples being added to the graph, such
        as for the entity itself, its individual attributes, etc.
        """
        try:
            id = doc["id"]
            eref = URIRef("http://cosmosdb.com/caig/{}".format(id))
            g.add((eref, RDF.type, CNS.Lib))
            g.add((eref, CNS.ln, Literal(doc["name"])))
            g.add((eref, CNS.lt, Literal(doc["libtype"])))
            g.add((eref, CNS.lic, Literal(doc["license_kwds"])))
            g.add((eref, CNS.kwds, Literal(doc["kwds"])))

            for dev in doc["developers"]:
                devref = URIRef("http://cosmosdb.com/caig/{}".format(dev))
                libref = URIRef("http://cosmosdb.com/caig/{}".format(id))
                g.add((eref, RDF.type, CNS.Dev))
                g.add((devref, CNS.developer_of, libref))
                g.add((libref, CNS.developed_by, devref))

            for dep_lib in doc["dependency_ids"]:
                pass
                libref = URIRef("http://cosmosdb.com/caig/{}".format(id))
                depref = URIRef("http://cosmosdb.com/caig/{}".format(dep_lib))
                g.add((libref, CNS.uses_lib, depref))
                g.add((depref, CNS.used_by_lib, libref))
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
