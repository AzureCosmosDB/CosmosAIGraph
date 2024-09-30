import os

from src.util.fs import FS
from src.util.template import Template

# This class is used to generate an *.owl RDF ontology file
# from a pair of summarized metadata files.  One metadata file
# summarizes the unique vertices/labels and their properties,
# and the other summarizes the unique edges/relationships.
#
# Chris Joakim, Microsoft


class OwlGenerator:

    def __init__(self):
        pass

    def generate(
        self,
        vertex_signatures_filename,
        edge_signatures_filename,
        namespace: str = "http://yourdomain.com/yourappname",
    ):
        """
        Generate the OWL ontology file from the given observed
        metadata filenames.  Produces file tmp/generated.owl
        and returns the XML.
        """
        vertex_signatures = FS.read_json(vertex_signatures_filename)
        edge_signatures = FS.read_json(edge_signatures_filename)
        classes = list()
        template_values = dict()
        template_values["ns"] = namespace
        template_values["spacer"] = ""

        for cname in self.collect_classnames(vertex_signatures, edge_signatures):
            data = dict()
            data["id"] = cname
            data["desc"] = ""
            classes.append(data)

        template_values["classes"] = classes
        template_values["class_attributes"] = self.collect_class_attributes(
            vertex_signatures
        )
        template_values["class_relationships"] = self.collect_relationships(
            edge_signatures
        )

        t = Template.get_template(os.getcwd(), "owl.txt")
        owl_xml = Template.render(t, template_values)
        FS.write("tmp/generated.owl", owl_xml)
        return owl_xml

    def collect_classnames(self, vertex_signatures, edge_signatures):
        classnames = dict()
        for sig in vertex_signatures:
            tokens = sig.split("|")
            classname = tokens[0]
            classnames[classname] = sig
        for sig in edge_signatures:
            tokens = sig.split("|")
            classname = tokens[0]
            classnames[classname] = sig
        return sorted(classnames.keys())

    def collect_class_attributes(self, vertex_signatures):
        attributes_dict = dict()  # a dictionary (attr names) of dictionaries (classes)
        attributes_list = list()  # an iterable list for jinga2 template
        for sig in vertex_signatures:
            tokens = sig.split("|")
            cname, aname, dtype = tokens[0], tokens[1], tokens[2]
            rdftype = "http://www.w3.org/2001/XMLSchema#string"
            if "'int'" in dtype:
                rdftype = "http://www.w3.org/2001/XMLSchema#int"

            # the same attribute name can be used in several classes; aggregate these
            if aname in attributes_dict.keys():
                aname_dict = attributes_dict[aname]
                aname_dict["classes"].append(cname)
            else:
                aname_dict = dict()
                aname_dict["aname"] = aname
                aname_dict["range"] = rdftype
                aname_dict["classes"] = [cname]
                attributes_dict[aname] = aname_dict
        FS.write_json(attributes_dict, "tmp/attributes_dict.json")

        for aname in sorted(attributes_dict.keys()):
            attributes_list.append(attributes_dict[aname])
        return attributes_list

    def collect_relationships(self, edge_signatures):
        relationships_dict = (
            dict()
        )  # a dictionary (attr names) of dictionaries (classes)
        relationships_list = list()  # an iterable list for jinga2 template
        for sig in edge_signatures:
            tokens = sig.split("|")  # "Project|hasStorage|ModelStorage"

            class1, rel_name, class2 = tokens[0], tokens[1], tokens[2]

            # the same attribute name can be used in several classes; aggregate these
            if rel_name == 'n/a':
                pass
            else:
                if rel_name in relationships_dict.keys():
                    rel_dict = relationships_dict[rel_name]
                    rel_dict["domain"][class1] = sig
                    rel_dict["range"][class2] = sig
                else:
                    rel_dict = dict()
                    rel_dict["rel_name"] = rel_name
                    rel_dict["domain"] = dict()
                    rel_dict["range"] = dict()
                    rel_dict["domain"][class1] = sig
                    rel_dict["range"][class2] = sig
                    relationships_dict[rel_name] = rel_dict

        for rel_name in sorted(relationships_dict.keys()):
            rel_dict = relationships_dict[rel_name]
            rel_dict["domain_list"] = sorted(rel_dict["domain"].keys())
            rel_dict["range_list"] = sorted(rel_dict["range"].keys())
            relationships_list.append(relationships_dict[rel_name])

        FS.write_json(relationships_dict, "tmp/relationships_dict.json")
        return relationships_list
