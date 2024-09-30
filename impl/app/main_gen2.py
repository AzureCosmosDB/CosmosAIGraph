"""
This is an OWL and RdflibTriplesBuilder code generator,
given just the relationships within the system as a CSV file.
The csv file contains the following three columns, and a header row:
source_label,relationship,destination_label

Usage:
    python main_gen2.py <function>
    python main_gen2.py generate <namespace>
    python main_gen2.py generate http://yourdomain.com/your_app_abbreviation
    python main_gen2.py generate http://nf.com/hg
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import json
import logging
import sys

from docopt import docopt
from dotenv import load_dotenv

from src.util.fs import FS
from src.util.owl_generator import OwlGenerator
from src.util.graph_builder_generator import GraphBuilderGenerator


class RelationshipsMetadata:
    """Simple class that reads the CSV file and exposes its' data."""

    def __init__(self, relationships_csv_file, attributes_csv_file):
        self.relationships_csv_file = relationships_csv_file
        self.attributes_csv_file = attributes_csv_file
        self.relationship_csv_rows = list()  # a list of dictionaries
        self.attributes_csv_rows = list()  # a list of dictionaries
        self.classes_dict = dict()
        self.attributes_list = list()

        # Read the Relationships CSV file, capture both the rows and the unique
        # Node/Class/Entity/Vertex names, and Relationship names.
        with open(self.relationships_csv_file, "r") as f:
            # header row: source_label,relationship,destination_label
            lines = f.readlines()
            for line_idx, line in enumerate(lines):
                if line_idx > 0:  # bypass the header row
                    tokens = line.strip().split(",")
                    if len(tokens) == 3:
                        row = dict()
                        row["source_label"] = tokens[0].replace(" ", "_")
                        row["relationship"] = tokens[1].replace(" ", "_")
                        row["destination_label"] = tokens[2].replace(" ", "_")
                        self.classes_dict[row["source_label"]] = 1
                        self.classes_dict[row["destination_label"]] = 1
                        self.relationship_csv_rows.append(row)
                    else:
                        logging.error("Invalid CSV line: {}".format(line))
                        continue

        with open(self.attributes_csv_file, "r") as f:
            # header row: source_label,attribute_name,datatype
            lines = f.readlines()
            for line_idx, line in enumerate(lines):
                if line_idx > 0:  # bypass the header row
                    tokens = line.strip().split(",")
                    if len(tokens) == 3:
                        row = dict()
                        row["source_label"] = tokens[0].replace(" ", "_").strip()
                        row["attribute_name"] = tokens[1].replace(" ", "_").strip()
                        row["datatype"] = tokens[2].strip()
                        self.attributes_csv_rows.append(row)
                    else:
                        logging.error("Invalid CSV line: {}".format(line))
                        continue

    def transform_to_standard_format(self) -> None:
        """
        Transform the CSV-based data to the standard/original format
        that is expected by classes OwlGenerator and RdflibTriplesBuilder.
        Save the transformed data as tmp files.
        """
        edge_signatures, vertex_signatures = dict(), dict()

        # CSV Relationships
        # {
        #   "source_label": "Member",
        #   "relationship": "Primary_Individual",
        #   "destination_label": "Student_Loan"
        # },
        # Required Edge Signatures format:
        # {
        #   "Movie|has_principal|Person": 10000,
        #   "Person|in_movie|Movie": 10000
        # }
        for row in self.relationship_csv_rows:
            sig = "{}|{}|{}".format(
                row["source_label"], row["relationship"], row["destination_label"]
            )
            edge_signatures[sig] = 1  # value isn't used

            sig = "{}|{}|{}".format(
                row["destination_label"], "n/a", row["source_label"]
            )
            edge_signatures[sig] = 1  # value isn't used

        # CSV Attributes
        # {
        #   "source_label": "Member",
        #   "attribute_name": "name",
        #   "datatype": "str"
        # },
        # Required Vertex Signatures format:
        # {
        #   "Movie|title|<class 'str'>": 10000,
        #   "Movie|year|<class 'int'>": 10000,
        #   "Movie|rating|<class 'int'>": 10000,
        #   "Movie|genre|<class 'str'>": 10000,
        #   "Person|name|<class 'str'>": 10000,
        #   "Person|born|<class 'int'>": 10000,
        #   "Person|died|<class 'str'>": 10000
        # }
        for row in self.attributes_csv_rows:
            sig = "{}|{}|<class '{}'>".format(
                row["source_label"], row["attribute_name"], row["datatype"].lower()
            )
            vertex_signatures[sig] = 1

        for row in self.relationship_csv_rows:
            sig = "{}|{}|{}".format(row["source_label"], "id", "str")
            vertex_signatures[sig] = 1

            sig = "{}|{}|{}".format(row["destination_label"], "id", "str")
            vertex_signatures[sig] = 1

        FS.write_json(edge_signatures, "tmp/gen2_edge_signatures.json")
        FS.write_json(vertex_signatures, "tmp/gen2_vertex_signatures.json")
        print("edge_signatures count:   {} ".format(len(edge_signatures)))
        print("vertex_signatures count: {} ".format(len(vertex_signatures)))

    def get_data(self) -> dict:
        """Bundle and return the CSV filenames and parsed data debugging purposes."""
        data = dict()
        data["relationships_csv_file"] = self.relationships_csv_file
        data["attributes_csv_file"] = self.attributes_csv_file
        data["classes_dict"] = self.classes_dict
        data["relationship_csv_rows"] = self.relationship_csv_rows
        data["attributes_csv_rows"] = self.attributes_csv_rows
        return data


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


def generate(relationships_csv_file, attributes_csv_file, namespace):
    metadata = RelationshipsMetadata(relationships_csv_file, attributes_csv_file)
    metadata.transform_to_standard_format()
    FS.write_json(metadata.get_data(), "tmp/gen2_data.json")

    generator = OwlGenerator()
    generator.generate(
        "tmp/gen2_vertex_signatures.json", "tmp/gen2_edge_signatures.json", namespace
    )

    generator = GraphBuilderGenerator()
    generator.generate("tmp/gen2_vertex_signatures.json")


def read_process_csv_file(csv_file):
    rows = list()  # a list of dictionaries
    with open(csv_file, "r") as f:
        lines = f.readlines()
        for line_idx, line in enumerate(lines):
            if line_idx > 0:  # bypass the header row
                tokens = line.strip().split(",")
                if len(tokens) == 3:
                    row = dict()
                    row["source_label"] = tokens[0]
                    row["relationship"] = tokens[0]
                    row["destination_label"] = tokens[0]
                    # source_label,relationship,destination_label
                else:
                    logging.error("Invalid CSV line: {}".format(line))
                    continue


if __name__ == "__main__":
    load_dotenv(override=True)
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            relationships_csv_file = (
                "../data/graph_input_metadata/GraphRelationships.csv"
            )
            attributes_csv_file = "../data/graph_input_metadata/GraphAttributes.csv"
            if func == "generate":
                namespace = sys.argv[2]
                generate(relationships_csv_file, attributes_csv_file, namespace)
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
