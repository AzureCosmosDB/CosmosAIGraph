from xml.sax import make_parser

from src.util.fs import FS
from src.util.owl_sax_handler import OwlSaxHandler

# This class uses the raw parsed data from the OwlSaxHandler class
# and reformats it as a JavaScript code suitable for vis.js, that
# can be copied & pasted into a HTML page, such as gen_sparql_console.html.
# This class is intended for command-line use, not for use in the web app.
#
# See https://visjs.org/
# See https://visjs.github.io/vis-network/examples/
# See https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js
# 
# Chris Joakim, Microsoft


class OwlVisualizer:

    def __init__(self, owl_filename):
        self.parser = make_parser()
        self.sax_handler = OwlSaxHandler()
        self.parser.setContentHandler(self.sax_handler)
        self.parser.parse(owl_filename)
        self.sax_data = self.sax_handler.get_data()
        FS.write_json(self.sax_data, "tmp/owl_sax_handler.json")

    def generate_visjs_content(self) -> str:
        lines = list()
        namespace = self.sax_data["xmlns"]
        classes = self.sax_data["classes"]
        last_classes_idx = len(classes) - 1
        object_properties = self.sax_data["object_properties"]

        lines.append('<script type="text/javascript">')
        lines.append('')
        lines.append('  // create an array with the nodes (i.e. - "entities")')
        lines.append('  var nodes = new vis.DataSet([')
        for idx, c in enumerate(classes):
            if idx < last_classes_idx:
                lines.append('    {{ id: "{}", label: "{}" }},'.format(c, c))
            else:
                lines.append('    {{ id: "{}", label: "{}" }}'.format(c, c))
        lines.append('  ]);')
        lines.append('')
        lines.append('  // create an array with the edges (i.e. - "relationships")')
        lines.append('  var edges = new vis.DataSet([')
        rel_names = sorted(object_properties.keys())
        print(rel_names)
        edge_types = self.collect_edge_types()
        last_edge_types_idx = len(edge_types) - 1
        for idx, edge_key in enumerate(sorted(edge_types.keys())):
            from_node = edge_key.split('|')[0]
            to_node = edge_key.split('|')[1]
            relationships = edge_types[edge_key]

            if idx < last_edge_types_idx:
                lines.append('    {{ from: "{}", to: "{}", title: "{}" }},'.format(
                    from_node, to_node, relationships))
            else:
                lines.append('    {{ from: "{}", to: "{}", title: "{}" }}'.format(
                    from_node, to_node, relationships))
                
        lines.append('  ]);')
        lines.append('')
        lines.append('  var html_container = document.getElementById("ontology_viz");')
        lines.append('  var graph_data = { nodes: nodes, edges: edges };')
        lines.append(self.graph_options())
        lines.append('  var network = new vis.Network(html_container, graph_data, graph_options);')
        lines.append('</script>')
        return "\n".join(lines)

    def collect_edge_types(self) -> dict:
        edges = dict()
        object_properties = self.sax_data["object_properties"]
        rel_names = sorted(object_properties.keys())
        for rel_name in rel_names:
            rel_obj = object_properties[rel_name]
            domains = rel_obj['domain']
            ranges = rel_obj['range']
            for d in domains:
                for r in ranges:
                    edge_key = "{}|{}".format(d, r)
                    if edge_key in edges.keys():
                        curr_value = edges[edge_key]
                        edges[edge_key] = "{}, {}".format(curr_value, rel_name)
                    else:
                        edges[edge_key] = rel_name
        FS.write_json(edges, "tmp/owl_visualizer_collect_edge_types.json")     
        return edges
    
    def graph_options(self) -> str:
        return """
  var graph_options = {
    edges: {
      arrows: {
        to: {
          enabled: true,
          scaleFactor: 0.2,
          type: "arrow"
        }
      },
      color: '#A9A9A9',
      font: '12px arial #A9A9A9',
      scaling: {
        label: true,
      },
      shadow: false,
      smooth: true,
    },
    physics:{
      enabled: true,
      repulsion: {
        centralGravity: 0.2,
        springLength: 200,
        springConstant: 0.05,
        nodeDistance: 200,
        damping: 0.09
      }
    }
  };""".strip()
    