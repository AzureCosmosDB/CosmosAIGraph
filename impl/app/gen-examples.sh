#!/bin/bash

python main_console.py generate_owl \
    ../data/graph_input_metadata/vertex_signatures_imdb.json \
    ../data/graph_input_metadata/edge_signatures_imdb.json \
    http://cosmosdb.com/imdb

python main_console.py generate_rdflib_triples_builder \
    ../data/graph_input_metadata/vertex_signatures_imdb.json