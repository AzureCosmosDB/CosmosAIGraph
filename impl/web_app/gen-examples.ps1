# This PowerShell script demonstrates command-line
# Code-generation in CosmosAIGraph.

# Generate an Ontology *.owl file from input data metadata.
# creates file tmp/generated.owl

python main.py generate_owl `
    ../../data/graph_input_metadata/vertex_signatures_imdb.json `
    ../../data/graph_input_metadata/edge_signatures_imdb.json `
    http://cosmosdb.com/imdb

# Generate class RdflibTriplesBuilder that loads the rdflib graph
# from your Cosmos DB Documents.
# creates file: tmp/rdflib_triples_builder.py

python main.py generate_rdflib_triples_builder `
    ../../data/graph_input_metadata/vertex_signatures_imdb.json

