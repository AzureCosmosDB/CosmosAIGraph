from xml.sax import make_parser

from src.util.fs import FS
from src.util.owl_sax_handler import OwlSaxHandler

# This class uses the raw parsed data from the OwlSaxHandler class
# and reformats it as a JSON data structure more suitable for D3.js.
# Chris Joakim, Microsoft


class OwlVisualizer:

    def __init__(self, owl_filename):
        self.parser = make_parser()
        self.handler = OwlSaxHandler()
        self.parser.setContentHandler(self.handler)
        self.parser.parse(owl_filename)
        FS.write_json(self.handler.get_data(), "tmp/owl_vizualizer.json")

    def get_d3_data(self):
        sax_data = self.handler.get_data()
        classes = sorted(sax_data["classes"])
        node_name_id_map = dict()
        node_num = 0
        edge_num = 1000

        d3_data = dict()
        d3_data["nodes"] = list()
        d3_data["edges"] = list()
        d3_data["attributes"] = list()
        d3_data["node_name_id_map"] = node_name_id_map

        for cidx, c in enumerate(classes):
            node_num = node_num + 1
            node = dict()
            node["id"] = node_num
            # node["idx"] = cidx
            node["name"] = c
            node["distance"] = 100
            node["strength"] = 100
            d3_data["nodes"].append(node)
            node_name_id_map[c] = node_num

        edge_num = 1000
        for name in sorted(sax_data["object_properties"].keys()):
            p = sax_data["object_properties"][name]
            domain_list, range_list = p["domain"], p["range"]
            for domain in domain_list:
                for ridx, range in enumerate(range_list):
                    if domain != range:
                        source_idx = node_name_id_map[domain]
                        target_idx = node_name_id_map[range]
                        edge_num = edge_num + 1
                        d3_data["edges"].append(
                            {
                                "id": edge_num,
                                "name": name,
                                "source": source_idx,
                                "source_type": domain,
                                "target": target_idx,
                                "target_type": range,
                                "distance": 100,
                                "strength": 100,
                                "weight": 1.0,
                            }
                        )

        for key in sorted(sax_data["datatype_properties"].keys()):
            p = sax_data["datatype_properties"][key]
            domain_list, range_list = p["domain"], p["range"]
            for domain in domain_list:
                for range in range_list:
                    if domain != range:
                        domain_idx = node_name_id_map[domain]
                        d3_data["attributes"].append(
                            {
                                "name": key,
                                "source": domain_idx,
                                "source_type": domain,
                                "target": range,
                            }
                        )
        FS.write_json(d3_data, "tmp/owl_vizualizer_d3_data.json")
        return d3_data
