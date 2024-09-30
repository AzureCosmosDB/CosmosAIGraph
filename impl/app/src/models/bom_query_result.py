import time

# Instances of this class represent the result of a Bill-of-Materials (BOM)
# SPARQL query vs the Libraries graph.
# Chris Joakim, Microsoft


class BomQueryResult:
    def __init__(self, libtype, libname, max_depth):
        type_name = "{}_{}".format(libtype, libname)
        self.data = dict()
        self.data["libtype"] = libtype
        self.data["libname"] = libname
        self.data["max_depth"] = int(max_depth)
        self.data["actual_depth"] = 0
        self.data["exception"] = None
        self.data["elapsed"] = -1
        self.data["bom_libs"] = dict()
        self.data["bom_libs"][type_name] = "unvisited"  # seed the bom_libs dict
        self.t1 = time.perf_counter()

    def get_data(self):
        return self.data

    def get_lib_count(self):
        return len(self.data["bom_libs"].keys())

    def get_bom_libs(self):
        return self.data["bom_libs"]

    def get_bom_libs_keys(self):
        return sorted(self.data["bom_libs"].keys())

    def get_bom_lib_by_key(self, key):
        return self.data["bom_libs"][key]

    def get_actual_depth(self):
        return self.data["actual_depth"]

    def increment_actual_depth(self):
        self.data["actual_depth"] = self.data["actual_depth"] + 1

    def set_lib_result(self, lib, obj):
        self.data["bom_libs"][lib] = obj

    def add_used_lib(self, lib, used_lib):
        self.data["bom_libs"][lib].append(used_lib)

    def add_unvisited(self, lib):
        if lib not in self.data["bom_libs"].keys():
            self.data["bom_libs"][lib] = "unvisited"

    def is_unvisited(self, lib):
        if lib is not None:
            if lib in self.get_bom_libs_keys():
                return self.data["bom_libs"][lib] == "unvisited"
        return True

    def set_exception(self, e):
        self.data["exception"] = str(e)

    def get_exception(self):
        return self.data["exception"]

    def has_exception(self):
        return self.data["exception"] != None

    def finish(self):
        t2 = time.perf_counter()
        self.data["elapsed"] = t2 - self.t1
