"""
Usage:
    python extract_ontology
    
Note: pre-define input_file and output_file variables
"""
# A graphml ontology extractor
# Aleksey Savateyev, Microsoft, 2025

import networkx as nx
from rdflib import RDF, Graph, Namespace, URIRef, Literal
import urllib.parse

input_file = "../data/graphml/summarized_graph.graphml"  # Path to the input GraphML file
output_file = "../data/ontologies/extracted_ontology.ttl"  # Path to the output OWL file

# Load the GraphML file
G = nx.read_graphml(input_file)

# Initialize an RDF graph
rdf_graph = Graph()

# Define namespaces
NS1 = Namespace("http://graphml.graphdrawing.org/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

rdf_graph.bind("ns1", NS1)
rdf_graph.bind("rdfs", RDFS)
rdf_graph.bind("owl", OWL)

# Map nodes to ontology classes or individuals
for node, data in G.nodes(data=True):
    node_label = data.get('label', node)  # Use 'label' attribute if available
    node_type = data.get('type', 'Class')  # Default type is 'Class'

    node_uri = URIRef(urllib.parse.quote(NS1[node], safe=':/#?&=@'))  # Create a URI for the node

    if node_type.lower() == 'class':  # If the node represents a class
        rdf_graph.add((node_uri, RDFS.subClassOf, OWL.Thing))  # Add as subclass of owl:Thing
        rdf_graph.add((node_uri, RDFS.label, Literal(node_label)))  # Add label
    elif node_type.lower() == 'individual':  # If the node represents an individual
        rdf_graph.add((node_uri, RDF.type, OWL.NamedIndividual))  # Mark as individual
        rdf_graph.add((node_uri, RDFS.label, Literal(node_label)))  # Add label

# Map edges to ontology relationships or properties
for source, target, data in G.edges(data=True):
    edge_label = data.get('label', 'relatedTo')  # Use 'label' attribute if available
    edge_type = data.get('type', 'ObjectProperty')  # Default type is 'ObjectProperty'

    source_uri = URIRef(urllib.parse.quote(NS1[source], safe=':/#?&=@'))
    target_uri = URIRef(urllib.parse.quote(NS1[target], safe=':/#?&=@'))

    if edge_type.lower() == 'objectproperty':  # If the edge represents an object property
        property_uri = URIRef(urllib.parse.quote(NS1[edge_label], safe=':/#?&=@'))  # Create a URI for the property
        rdf_graph.add((property_uri, RDF.type, OWL.ObjectProperty))  # Mark as ObjectProperty
        rdf_graph.add((property_uri, RDFS.label, Literal(edge_label)))  # Add label
        rdf_graph.add((source_uri, property_uri, target_uri))  # Link source to target via property
    elif edge_type.lower() == 'subclassof':  # If the edge represents a subclass relationship
        rdf_graph.add((source_uri, RDFS.subClassOf, target_uri))  # Add subclass relationship

# Save the RDF graph to an OWL file
rdf_graph.serialize(output_file, format="ttl")
print("Ontology has been successfully extracted and saved as 'extracted_ontology.ttl'.")


