"""
Usage:
    python graphml2ttl
    
Note: pre-define input_folder and output_folder variables
"""

# A graphml to Turtle converter
# Aleksey Savateyev, Microsoft, 2025

import os
import xml.etree.ElementTree as ET
from rdflib import Graph, Literal, Namespace, URIRef
import urllib.parse

def is_valid_uri(uri):
    try:
        result = urllib.parse.urlparse(uri)
        return all([result.scheme, result.netloc])
    except:
        return False

def convert_graphml_to_ttl(input_folder, output_folder):
    ns = Namespace("http://graphml.graphdrawing.org/")
    
    for filename in os.listdir(input_folder):
        if filename.endswith('.graphml'):
            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, filename.replace('.graphml', '.ttl'))
            g = Graph()
            tree = ET.parse(input_file)
            root = tree.getroot()
            
            # Modified URI creation with proper encoding
            def create_uri(identifier):
                return URIRef(ns + urllib.parse.quote(identifier, safe=''))

            # Process nodes
            for node in root.findall('.//{http://graphml.graphdrawing.org/xmlns}node'):
                node_id = node.get('id')
                node_uri = create_uri(node_id)
                g.add((node_uri, ns.type, ns.Node))
                
                for data in node.findall('{http://graphml.graphdrawing.org/xmlns}data'):
                    key = data.get('key')
                    value = data.text
                    if data.get('type') == 'uri' and value:
                        parsed_value = urllib.parse.urlparse(value)
                        if not parsed_value.scheme:
                            value = f"http://{value}"  # Add default scheme if missing
                        encoded_value = urllib.parse.quote(value, safe=':/#?&=@')
                        g.add((node_uri, ns[key], URIRef(encoded_value)))
                    else:
                        g.add((node_uri, ns[key], Literal(value)))

            # Process edges
            for edge in root.findall('.//{http://graphml.graphdrawing.org/xmlns}edge'):
                source = create_uri(edge.get('source'))
                target = create_uri(edge.get('target'))
                g.add((source, ns.edge, target))
                
                for data in edge.findall('{http://graphml.graphdrawing.org/xmlns}data'):
                    key = data.get('key')
                    value = data.text
                    if data.get('type') == 'uri' and value:
                        parsed_value = urllib.parse.urlparse(value)
                        if not parsed_value.scheme:
                            value = f"http://{value}"
                        encoded_value = urllib.parse.quote(value, safe=':/#?&=@')
                        g.add((source, ns[key], URIRef(encoded_value)))
                    else:
                        g.add((source, ns[key], Literal(value)))

            g.serialize(output_file, format='turtle')

input_folder = '../data/graphml'
output_folder = '../data/ttl'
convert_graphml_to_ttl(input_folder, output_folder)
