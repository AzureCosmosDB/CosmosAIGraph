"""
Usage:
    python extract_ontology2
    
Note: pre-define input_file and output_file variables
"""
# A graphml ontology extractor
# Aleksey Savateyev, Microsoft, 2025

import urllib
from rdflib import Graph, Literal, Namespace, RDF, RDFS

input_file = "../data/graphml/summarized_graph.graphml"  # Path to the input GraphML file
output_file = "../data/ontologies/extracted_ontology.ttl"  # Path to the output OWL file



import networkx as nx
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL

def graphml_to_owl(graphml_file, owl_file):
    # Read the graphml file
    G = nx.read_graphml(graphml_file)
    
    # Create a new RDF graph
    rdf_graph = Graph()
    # Define the ontology namespace (replace with your ontology namespace)
    ns = Namespace("http://graphml.graphdrawing.org/")
    rdf_graph.bind("ns1", ns)
    
    # Define namespaces
    ns = URIRef("http://graphml.graphdrawing.org/")
    
    # Iterate through nodes and add them to the RDF graph
    for node_id, node_data in G.nodes(data=True):
        node_uri = URIRef(urllib.parse.quote(ns+node_id, safe=':/#?&=@'))
        rdf_graph.add((node_uri, RDF.type, OWL.Class))
        # for attr, value in node_data.items():
        #     rdf_graph.add((node_uri, URIRef(urllib.parse.quote(ns+attr, safe=':/#?&=@')), Literal(value)))
    
    # Iterate through edges and add them to the RDF graph
    for subject_id, object_id, edge_data in G.edges(data=True):
        subject_uri = URIRef(urllib.parse.quote(ns+str(subject_id), safe=':/#?&=@'))
        object_uri = URIRef(urllib.parse.quote(ns+str(object_id), safe=':/#?&=@'))
        rdf_graph.add((subject_uri, RDF.type, OWL.ObjectProperty))
        rdf_graph.add((subject_uri, RDFS.range, object_uri))
        # for attr, value in edge_data.items():
        #     rdf_graph.add((subject_uri, URIRef(urllib.parse.quote(ns+attr, safe=':/#?&=@')), Literal(value)))

    
    # Serialize the RDF graph to an OWL file
    rdf_graph.serialize(destination=owl_file, format="turtle")
    print("Ontology has been successfully extracted and saved as '{}'.", owl_file)
# Example usage
graphml_to_owl(input_file, output_file)