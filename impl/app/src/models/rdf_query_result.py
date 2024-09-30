import time

# Instances of this class represent the result of a generic RDF SPARQL query.
# Chris Joakim, Microsoft


class RdfQueryResult:
    def __init__(self, sparql):
        self.data = dict()
        self.data["sparql"] = sparql
        self.data["rows"] = list()
        self.data["results"] = list()
        self.data["exception"] = None
        self.data["elapsed"] = -1
        self.data["row_count"] = 0
        self.t1 = time.perf_counter()

    def get_data(self):
        return self.data

    def add_row(self, row):
        if row != None:
            self.data["rows"].append(row)

    def get_rows(self):
        return self.data["rows"]

    def get_results(self):
        return self.data["results"]

    def set_results(self, results):
        self.data["results"] = results

    def set_exception(self, e):
        self.data["exception"] = str(e)

    def get_exception(self):
        return self.data["exception"]

    def has_exception(self):
        return self.data["exception"] != None

    def prune_data(self):
        del self.data["rows"]

    def finish(self):
        self.data["row_count"] = len(self.data["results"])
        t2 = time.perf_counter()
        self.data["elapsed"] = t2 - self.t1
