"""
This program is experimental, for AI-based graph generation of the HotPotQA dataset.
See file private/common_data/HotPotQA/combined_ontology.ttl in this repo.
Usage:
    python main_hotpot.py read_combined_ontology
    Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import json
import logging
import os
import sys
import textwrap
import time

from docopt import docopt
from dotenv import load_dotenv

import rdflib
from rdflib import Graph, Literal, RDF, URIRef
from rdflib.namespace import Namespace

from src.services.config_service import ConfigService
from src.services.logging_level_service import LoggingLevelService
from src.util.fs import FS


logging.basicConfig(
    format="%(asctime)s - %(message)s", level=LoggingLevelService.get_level()
)


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


def read_combined_ontology():
    graph_namespace = "http://example.org/ontology#"
    graph_namespace_alias = "ontology"
    CNS = Namespace(graph_namespace)
    ontology_file = "../private/common_data/HotPotQA/combined_ontology_edited.ttl"
    g = Graph()
    g.bind(graph_namespace_alias, CNS)
    g.parse(ontology_file, format="ttl")
    print(g)


if __name__ == "__main__":
    load_dotenv(override=True)

    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            if func == "read_combined_ontology":
                read_combined_ontology()
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
