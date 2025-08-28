# Instances of this class are used to reduce a given Cosmos DB
# JSON document to only the pertinent attributes, and truncate
# their values if they're long.
#
# Chris Joakim, Microsoft, 2025


class CosmosDocFilter:

    def __init__(self, cosmos_doc):
        self.cosmos_doc = cosmos_doc

    def filter_library(self, additional_attrs=list()):
        """
        Reduce the given Cosmos DB document to only the pertinent attributes.
        """
        filtered = dict()
        filtered_attrs = self.general_attributes()
        if self.cosmos_doc is not None:
            for attr in self.cosmos_doc.keys():
                if attr in filtered_attrs:
                    filtered[attr] = self.cosmos_doc[attr]
                if additional_attrs is not None:
                    if attr in additional_attrs:
                        filtered[attr] = self.cosmos_doc[attr]
        return filtered
    
    def general_attributes(self):
        return [
            "name",
            "description",
            "summary",
            "documentation_summary",
            "kwds",
            "dependency_ids",
            "developers",
            "release_count",
        ]
    
    def filter_for_rag_data(self):
        filtered = dict()
        filtered_attrs = self.rag_attributes()
        if self.cosmos_doc is not None:
            for attr in self.cosmos_doc.keys():
                if attr in filtered_attrs:
                    if attr == "dependency_ids":
                        filtered[attr] = list()
                        for dep_id in self.cosmos_doc[attr]:
                            filtered[attr].append(
                                dep_id[5:]
                            )  # 'pypi_jinja2' becomes 'jinja2'
                    elif attr == "description":
                        filtered[attr] = self.cosmos_doc[attr][:255].replace("\n", " ")
                    elif attr == "summary":
                        filtered[attr] = self.cosmos_doc[attr][:255].replace("\n", " ")
                    elif attr == "documentation_summary":
                        filtered[attr] = self.cosmos_doc[attr][:1024].replace("\n", " ")
                    else:
                        filtered[attr] = self.cosmos_doc[attr]
        return filtered

    def rag_attributes(self):
        return [
            "name",
            "description",
            "summary",
            "documentation_summary",
            "kwds",
            "dependency_ids",
            "developers",
            "release_count",
        ]

    def filter_out_embedding(self, embedding_attr = "embedding"):
        """
        Remove embedding fromCosmos DB documents and truncate some known ones.
        """
        filtered = dict()
        #filtered_attrs = self.rag_attributes()
        if self.cosmos_doc is not None:
            for attr in self.cosmos_doc.keys():
                if attr != embedding_attr:
                    if attr == "dependency_ids":
                        filtered[attr] = list()
                        for dep_id in self.cosmos_doc[attr]:
                            filtered[attr].append(
                                dep_id[5:]
                            )  # 'pypi_jinja2' becomes 'jinja2'
                    elif attr == "description":
                        filtered[attr] = self.cosmos_doc[attr][:255]#.replace("\n", " ")
                    elif attr == "summary":
                        filtered[attr] = self.cosmos_doc[attr][:255]#.replace("\n", " ")
                    elif attr == "documentation_summary":
                        filtered[attr] = self.cosmos_doc[attr][:1024]#.replace("\n", " ")
                    else:
                        filtered[attr] = self.cosmos_doc[attr][:1024] if isinstance(self.cosmos_doc[attr], str) else self.cosmos_doc[attr]

        return filtered


    def filter_for_vector_search(self):
        """
        Reduce the given Cosmos DB document to only the pertinent attributes
        """
        filtered = dict()
        filtered_attrs = self.vector_search_attributes()
        if self.cosmos_doc is not None:
            for attr in self.cosmos_doc.keys():
                if attr in filtered_attrs:
                    filtered[attr] = self.cosmos_doc[attr]
        return filtered

    def vector_search_attributes(self):
        return [
            "name",
            "description",
            "summary",
            "documentation_summary",
            "kwds",
            "dependency_ids",
            "developers",
            "release_count",
            "embedding",
        ]
