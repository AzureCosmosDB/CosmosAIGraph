"""
Usage:

python graphml2ttl.py
Note: pre-define input_graphml, ontology_ttl and instances_ttl variables

"""

# A graphml ontology extractor
# Aleksey Savateyev, Microsoft, 2025

from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
import xml.etree.ElementTree as ET
import re

input_graphml = "../data/graphml/create_clustered_graph.graphml" # Path to the input GraphML file
instances_ttl = "../data/ttl/clustered_graph.ttl" # Path to the output RDF Turtle file
ontology_ttl = "../data/ontologies/clustered_graph_ontology.ttl" # Path to the output ontology TTL file

def sanitize_uri(value):
    """Convert strings to URI-safe format"""
    return re.sub(r'[^a-zA-Z0-9/\\.\\~!*\\\'\\(\\)\\-]', '_', str(value).strip())

def graphml_to_ttl_with_ontology(graphml_path, instance_path, ontology_path):
    # Initialize graphs
    instance_g = Graph()
    ontology_g = Graph()
    # Define namespaces
    BASE = Namespace("http://example.org/ontology/")
    INST = Namespace("http://example.org/instances/")
    ontology_g.bind("base", BASE)
    ontology_g.bind("owl", OWL)
    instance_g.bind("inst", INST)
    instance_g.bind("base", BASE)
    # Parse GraphML
    tree = ET.parse(graphml_path)
    root = tree.getroot()
    ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}
    # Extract attribute keys and build ontology
    keys = {}
    for key in root.findall('.//graphml:key', ns):
        key_id = key.attrib['id']
        keys[key_id] = {
            'for': key.attrib['for'],
            'name': key.attrib['attr.name'],
            'type': key.attrib['attr.type']
        }
        # Create datatype properties in ontology with correct types
        prop_uri = BASE[key.attrib['attr.name']]
        if key.attrib['for'] == 'node':
            ontology_g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            ontology_g.add((prop_uri, RDFS.domain, BASE.Node))
        else:
            ontology_g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            ontology_g.add((prop_uri, RDFS.domain, BASE.Relationship))
        # Add range based on GraphML type
        xsd_type = get_xsd_type(key.attrib['attr.type'])
        ontology_g.add((prop_uri, RDFS.range, xsd_type))
    # Create ontology classes and single relationship
    ontology_g.add((BASE.Node, RDF.type, OWL.Class))
    ontology_g.add((BASE.Relationship, RDF.type, OWL.Class))
    ontology_g.add((BASE.relatesTo, RDF.type, OWL.ObjectProperty))
    ontology_g.add((BASE.relatesTo, RDFS.domain, BASE.Node))
    ontology_g.add((BASE.relatesTo, RDFS.range, BASE.Node))
    # Add relatedBy as the inverse of relatesTo
    ontology_g.add((BASE.relatedBy, RDF.type, OWL.ObjectProperty))
    ontology_g.add((BASE.relatedBy, OWL.inverseOf, BASE.relatesTo))
    ontology_g.add((BASE.relatedBy, RDFS.domain, BASE.Node))
    ontology_g.add((BASE.relatedBy, RDFS.range, BASE.Node))
    # Node ID to URI mapping (using both XML IDs and data IDs)
    node_map = {} # Maps GraphML node IDs to URIs
    id_map = {} # Maps data IDs (d0) to URIs
    # Process nodes with strict type enforcement
    for node in root.findall('.//graphml:node', ns):
        data = {}
        for d in node.findall('graphml:data', ns):
            key = keys[d.attrib['key']]
            value = convert_value(d.text, key['type'])
            data[key['name']] = value
        # Create URI using title if available, otherwise use human_readable_id or data ID
        title = data.get('title')
        human_id = data.get('human_readable_id')
        node_id = data.get('id')
        # Priority: title > human_readable_id > node ID > XML ID
        if title:
            node_uri = INST[sanitize_uri(title)]
        elif human_id:
            node_uri = INST[f"id_{sanitize_uri(human_id)}"]
        elif node_id:
            node_uri = INST[f"id_{sanitize_uri(node_id)}"]
        else:
            node_uri = INST[f"xmlid_{sanitize_uri(node.attrib['id'])}"]
        # Map all possible identifiers
        node_map[node.attrib['id']] = node_uri
        if node_id:
            id_map[node_id] = node_uri
        instance_g.add((node_uri, RDF.type, BASE.Node))
        for attr, value in data.items():
            if value is not None and attr != 'title':
                pred = BASE[attr]
                if attr == 'text_unit_ids':
                    for item in value.split(', '):
                        instance_g.add((node_uri, pred, Literal(item.strip())))
                else:
                    instance_g.add((node_uri, pred, Literal(value, datatype=get_xsd_type(keys[next(k for k,v in keys.items() if v['name'] == attr)]['type']))))
    # Process edges with comprehensive node mapping
    for edge in root.findall('.//graphml:edge', ns):
        data = {}
        for d in edge.findall('graphml:data', ns):
            key = keys[d.attrib['key']]
            value = convert_value(d.text, key['type'])
            data[key['name']] = value
        # Handle source/target with multiple lookup strategies
        source_id = edge.attrib['source']
        target_id = edge.attrib['target']
        # Lookup order: node_map (XML ID) -> id_map (data ID) -> create URI from ID
        source = node_map.get(source_id) or id_map.get(source_id) or INST[f"xmlid_{sanitize_uri(source_id)}"]
        target = node_map.get(target_id) or id_map.get(target_id) or INST[f"xmlid_{sanitize_uri(target_id)}"]
        # Create relationship instance with properties
        relationship = BNode()
        instance_g.add((source, BASE.relatesTo, target))
        instance_g.add((target, BASE.relatedBy, source))  # Add the inverse relationship
        instance_g.add((relationship, RDF.type, BASE.Relationship))
        instance_g.add((relationship, BASE.source, source))
        instance_g.add((relationship, BASE.target, target))
        # Add all edge properties
        for attr, value in data.items():
            if attr not in ['id']:
                pred = BASE[attr]
                if attr == 'text_unit_ids':
                    for item in value.split(', '):
                        instance_g.add((relationship, pred, Literal(item.strip())))
                else:
                    instance_g.add((relationship, pred, Literal(value, datatype=get_xsd_type(keys[next(k for k,v in keys.items() if v['name'] == attr)]['type']))))
    # Serialize
    instance_g.serialize(destination=instance_path, format="turtle")
    ontology_g.serialize(destination=ontology_path, format="turtle")

def convert_value(value, graphml_type):
    """Convert values according to GraphML type specifications"""
    if not value:
        return None
    try:
        if graphml_type == 'long':
            return int(float(value)) # Handle scientific notation
        elif graphml_type == 'double':
            return float(value)
        return value
    except (ValueError, TypeError):
        return value

def get_xsd_type(graphml_type):
    """Map GraphML types to XSD types"""
    return {
        'string': XSD.string,
        'long': XSD.integer,
        'double': XSD.double
    }.get(graphml_type, XSD.string)

# Usage
graphml_to_ttl_with_ontology(
    input_graphml,
    instances_ttl,
    ontology_ttl
)
