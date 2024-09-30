# Instances of this class are used as the data structure that is returned
# from the RagDataService get_rag_docs() method.  This result object is
# useful to the UI to explain the actions and processing of the application.
# Chris Joakim, Microsoft


class RAGDataResult:

    def __init__(self):
        self.data = dict()
        self.data["type"] = "RAGDataResult"
        self.data["user_text"] = ""
        self.data["strategy"] = list()
        self.data["sparql"] = ""
        self.data["query"] = ""
        self.data["rag_docs"] = list()
        self.data["rag_doc_count"] = -1

    def finish(self):
        self.data["rag_doc_count"] = len(self.data["rag_docs"])

    def set_attr(self, attr_name, value):
        if attr_name is not None:
            if value is not None:
                self.data[attr_name] = value

    def get_data(self):
        return self.data

    def get_rag_docs(self):
        return self.data["rag_docs"]

    def add_doc(self, doc):
        self.data["rag_docs"].append(doc)

    def get_strategy(self):
        return ",".join(self.data["strategy"])

    def has_db_rag_docs(self):
        """return true if the strategy is 'db' and length of rag_docs > 0"""
        if self.get_strategy() == "db":
            if len(self.get_rag_docs()) > 0:
                return True
        return False

    def has_graph_rag_docs(self):
        """return true if the strategy is 'graph' and length of rag_docs > 0"""
        if self.get_strategy() == "graph":
            if len(self.get_rag_docs()) > 0:
                return True
        return False

    def set_user_text(self, value):
        if value is not None:
            self.data["user_text"] = str(value)

    def set_sparql(self, value):
        if value is not None:
            self.data["sparql"] = str(value)

    def get_sparql(self):
        return self.data["sparql"]

    def set_query(self, value):
        if value is not None:
            self.data["query"] = str(value)

    def get_query(self):
        return self.data["query"]

    def set_rag_docs(self, value):
        if value is not None:
            self.data["rag_docs"] = value

    def add_strategy(self, value):
        if value is not None:
            self.data["strategy"].append(str(value))

    def as_system_prompt_text(self):
        prompt_lines = list()
        docs = self.data["rag_docs"]
        if len(docs) > 0:
            prompt_lines.append(
                "Use the following {} Documents to answer the user query.".format(
                    len(docs)
                )
            )
            prompt_lines.append(
                "Each Document has four attributes; one per line: name, type, summary, and documentation."
            )
            prompt_lines.append(
                "Each Document starts and ends with '###' to make it easy to parse."
            )

        for doc in self.data["rag_docs"]:
            prompt_lines.append("\nDocument ###")
            prompt_lines.append("name: {}".format(doc["name"]))
            prompt_lines.append("type: {}".format(doc["libtype"]))
            prompt_lines.append("summary: {}".format(doc["summary"]))
            prompt_lines.append(
                "documentation: {}".format(doc["documentation_summary"])
            )
            prompt_lines.append("###")

        return "\n".join(prompt_lines)
