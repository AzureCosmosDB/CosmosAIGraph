import logging
import time

from rdflib import Graph
from rdflib.namespace import Namespace
from rdflib.extras.infixowl import AllClasses, AllProperties, GetIdentifiedClasses

# This class uses the rdflib library to explore and display
# the contents of an OWL ontology file.
#
# Chris Joakim, Microsoft


class OwlExplorer:

    def __init__(self, owl_file: str, custom_namespace: str, custom_namespace_bind="c"):
        self.CNS = Namespace(custom_namespace)
        print("OwlExplorer#__init__ - owl:  {}".format(owl_file))
        print("OwlExplorer#__init__ - cns:  {}".format(custom_namespace))
        print("OwlExplorer#__init__ - bind: {}".format(custom_namespace_bind))
        self.g = Graph()
        self.g.bind(custom_namespace_bind, self.CNS)
        self.g.parse(owl_file, format="xml")

    def display(self) -> None:
        print("=== OwlExplorer GetIdentifiedClasses ===")
        classes = list(GetIdentifiedClasses(self.g))
        for idx, c in enumerate(classes):
            print("{} {}".format(idx, c))

        print("=== OwlExplorer AllClasses ===")
        classes = list(AllClasses(self.g))
        for idx, c in enumerate(classes):
            print("{} {}".format(idx, c))

        print("=== OwlExplorer AllProperties ===")
        properties = list(AllProperties(self.g))
        for idx, p in enumerate(properties):
            print("{} {}".format(idx, p))

        print("=== OwlExplorer CNS ===")
        print("CNS type: {}".format(str(type(self.CNS))))  # rdflib.namespace.Namespace
        print(self.CNS["hasProject"])

    def iterate_print_graph(self, comment=""):
        print("OwlExplorer#iterate_print_graph start {} ...".format(comment))
        count = 0
        t1 = time.perf_counter()
        for s, p, o in self.g:  # Iterate the graph, counting and displaying the triples
            count = count + 1
            print("{} {} {}".format(s, p, o))
        t2 = time.perf_counter()
        seconds = f"{(t2 - t1):.9f}"
        logging.critical(
            "OwlExplorer#iterate_print_graph completed, count: {} seconds: {}".format(
                count, seconds
            )
        )
