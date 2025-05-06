"""
Usage:
python graphml2ontology.py
Note: pre-define input_graphml, ontology_ttl and instances_ttl variables
"""

from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
import xml.etree.ElementTree as ET
import re
import json

input_graphml = "../data/graphml/create_clustered_graph.graphml"
instances_ttl = "../data/ttl/clustered_graph.ttl"
ontology_ttl = "../data/ontologies/clustered_graph_ontology.ttl"
#text_units_json = "../data/graphml/create_base_text_units.parquet.as.json"

def sanitize_uri(value):
    return re.sub(r'[^a-zA-Z0-9-]', '_', str(value).strip())

def extract_title(text):
    """Extract title from text field using regex"""
    match = re.search(r'title:\s*(.*?)(\.\n|\n|$)', text)
    return match.group(1).strip() if match else None

# def load_text_units(json_path):
#     id_to_text = {}
#     with open(json_path, 'r') as f:
#         for line in f:
#             try:
#                 unit = json.loads(line)
#                 if 'id' in unit and 'text' in unit:
#                     id_to_text[unit['id']] = unit['text']
#             except json.JSONDecodeError as e:
#                 print(f"Error decoding JSON: {e}")
#                 continue
#     return id_to_text

def graphml_to_ttl_with_ontology(graphml_path, instance_path, ontology_path):
    # Load text units data
    # id_to_title = {}
    # text_units = load_text_units(text_units_json)
    # for id,text in text_units.items():
    #     title = extract_title(text)
    #     if title:
    #         id_to_title[id] = title
            
    # Initialize graphs
    #instance_g = Graph()
    ontology_g = Graph()

    # Define namespaces
    BASE = Namespace("http://example.org/ontology/")
    INST = Namespace("http://example.org/instances/")

    ontology_g.bind("base", BASE)
    ontology_g.bind("owl", OWL)
    ontology_g.bind("inst", INST)    
    #instance_g.bind("inst", INST)
    #instance_g.bind("base", BASE)

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

        # Create datatype properties in ontology
        prop_uri = BASE[key.attrib['attr.name']]
        xsd_type = get_xsd_type(key.attrib['attr.type'])
        
        ontology_g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        ontology_g.add((prop_uri, RDFS.domain, BASE.Node))
        ontology_g.add((prop_uri, RDFS.range, xsd_type))

    # Manually add title property if not defined in GraphML
    if not any(v['name'] == 'title' for v in keys.values()):
        ontology_g.add((BASE.title, RDF.type, OWL.DatatypeProperty))
        ontology_g.add((BASE.title, RDFS.domain, BASE.Node))
        ontology_g.add((BASE.title, RDFS.range, XSD.string))

    # Existing ontology setup...
    ontology_g.add((BASE.Node, RDF.type, OWL.Class))
    ontology_g.add((BASE.relatesTo, RDF.type, OWL.ObjectProperty))
    ontology_g.add((BASE.relatesTo, RDFS.domain, BASE.Node))
    ontology_g.add((BASE.relatesTo, RDFS.range, BASE.Node))
    ontology_g.add((BASE.relatedBy, RDF.type, OWL.ObjectProperty))
    ontology_g.add((BASE.relatedBy, OWL.inverseOf, BASE.relatesTo))

    # Process nodes
    node_map = {}
    for node in root.findall('.//graphml:node', ns):
        data = {}
        for d in node.findall('graphml:data', ns):
            key = keys[d.attrib['key']]
            value = convert_value(d.text, key['type'])
            data[key['name']] = value

        # URI generation
        human_id = data.get('human_readable_id')
        xml_id = node.attrib['id']
        
        if human_id:
            node_uri = INST[sanitize_uri(human_id)]
        else:
            node_uri = INST[f"xmlid_{sanitize_uri(xml_id)}"]
            
        if 'title' in data:
            node_id = data.get('title')
            node_uri = INST[sanitize_uri(node_id)]

        node_map[xml_id] = node_uri
        #instance_g.add((node_uri, RDF.type, BASE.Node))
        has_non_alphanumeric = any(not char.isalnum() for char in node_id)
        if not has_non_alphanumeric and not any(char.isdigit() for char in node_id) and not node_id.startswith("_") and not node_id.startswith("-"):
            ontology_g.add((node_uri, RDF.type, BASE.Node))

        # Add title as property if present
        # if 'title' in data:
        #     instance_g.add((node_uri, BASE.title, Literal(data['title'])))

        # Add other properties
        #for attr, value in data.items():
            # if attr != 'title' and value is not None:
            #     pred = BASE[attr]
            #     instance_g.add((node_uri, pred, Literal(value)))
    # Process edges with comprehensive node mapping
    # for edge in root.findall('.//graphml:edge', ns):
    #     source_id = edge.attrib['source']
    #     target_id = edge.attrib['target']
    #     source = node_map.get(source_id)
    #     target = node_map.get(target_id)

    #     # Create reified statement for edge properties
    #     statement = BNode()
    #     instance_g.add((statement, RDF.type, RDF.Statement))
    #     instance_g.add((statement, RDF.subject, source))
    #     instance_g.add((statement, RDF.predicate, BASE.relatesTo))
    #     instance_g.add((statement, RDF.object, target))

    #     # Add edge properties to the statement
    #     for d in edge.findall('graphml:data', ns):
    #         key = d.attrib['key']
    #         prop_name = keys[key]['name']
    #         value = convert_value(d.text, keys[key]['type'])
    #         instance_g.add((statement, BASE[prop_name], Literal(value)))
            
    #         if prop_name == 'text_unit_ids':
    #             titles = []
    #             for tid in d.text.split(', '):
    #                 if tid.strip() in id_to_title:
    #                     titles.append(id_to_title[tid.strip()])
    #             if titles:
    #                 instance_g.add((statement, BASE.sourceFiles, Literal(', '.join(titles))))

    #     # Add direct relationships
    #     instance_g.add((source, BASE.relatesTo, target))
    #     instance_g.add((target, BASE.relatedBy, source))
        
    # # Serialize
    # instance_g.serialize(destination=instance_path, format="turtle")
    ontology_g.serialize(destination=ontology_path, format="turtle")
    ontology_g.serialize(destination=ontology_path+".owl", format="xml")

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
