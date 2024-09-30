import json
import logging
import time

from src.services.config_service import ConfigService
from src.services.graph_builder import GraphBuilder
from src.models.internal_models import OwlInfo
from src.models.bom_query_result import BomQueryResult
from src.models.rdf_query_result import RdfQueryResult
from src.util.fs import FS
from src.util.sparql_formatter import SparqlFormatter
from src.util.sparql_template import SparqlTemplate

# Instances of this class contain the in-memory rdflib graph,
# and are use to interact with and query the graph via the SPARQL query syntax.
# See https://rdflib.readthedocs.io/en/stable/
# Chris Joakim, Microsoft


class GraphService:

    def __init__(self, opts={}):
        self.opts = opts
        self.gb = None

    async def initialize(self, gb: GraphBuilder):
        self.gb = gb
        self.graph = await self.gb.build()

    async def reload(self):
        self.graph = await self.gb.build()

    def liveness_check(self) -> dict:
        """
        Return a dict containing the health status of this GraphService.
        The dict resembles a LivenessModel.
        """
        alive = False
        rows_read = 0
        try:
            if self.graph == None:
                rows_read = -1
            else:
                for row in self.graph.query("SELECT * WHERE { ?s ?p ?o . } LIMIT 100"):
                    rows_read = rows_read + 1
                if rows_read > 90:  # 100+ rows are expected, including the OWL content
                    alive = True
        except Exception as e:
            rows_read = -2
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        data = dict()
        data["alive"] = alive
        data["rows_read"] = rows_read
        data["epoch"] = time.time()
        return data

    def owl_info(self) -> OwlInfo:
        """Return a dict containing the owl filename and owl content"""
        resp_obj = dict()
        resp_obj["ontology_file"] = ""
        resp_obj["owl"] = ""
        resp_obj["error"] = None
        try:
            ontology_file = ConfigService.graph_source_owl_filename()
            resp_obj["ontology_file"] = ontology_file
            resp_obj["owl"] = FS.read(ontology_file)
        except Exception as e:
            resp_obj["error"] = str(e)
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        return resp_obj

    def query(self, sparql) -> RdfQueryResult:
        """
        Query the in-memory graph with the given SPARQL.
        Return a RdfQueryResult object.
        """
        rqr = RdfQueryResult(sparql)
        try:
            if sparql == None:
                rqr.set_exception("given sparql is None")
                return rqr
            sparql = SparqlFormatter().pretty(sparql)  # ensure a PREFIX is present

            if self._valid_query(sparql):
                logging.info("GraphService - query: {}".format(sparql))
                for row in self.graph.query(sparql):
                    # row is an instance of <class 'rdflib.query.ResultRow'>
                    rqr.add_row(row)
                rqr.set_results(self._reduce_query_results(rqr.get_rows()))
            else:
                rqr.set_exception("invalid query; not executed")
        except Exception as e:
            rqr.set_exception(str(e))
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        rqr.finish()
        return rqr

    def bom_query(self, libtype, libname, max_depth=3) -> BomQueryResult:
        """
        Query/Traverse the in-memory graph to determine the bill-of-material for the given libname.
        Return a BomQueryResult object.
        """
        bqr = BomQueryResult(libtype, libname, max_depth)
        try:
            if libname == None:
                bqr.set_exception("given bom root libname is None")
                return bqr
            if max_depth < 1:
                bqr.set_exception("max_depth is less than 1")
                return bqr
            continue_to_process = True
            for i in range(max_depth):  # list(range(3)) -> [0, 1, 2]
                if continue_to_process == True:
                    bqr.increment_actual_depth()
                    begin_lib_count = bqr.get_lib_count()
                    self._iterate_bom(i, bqr, libtype)
                    after_lib_count = bqr.get_lib_count()
                    if after_lib_count == begin_lib_count:
                        continue_to_process = False
                        logging.info(
                            "get_bill_of_materials terminating at depth: {}".format(i)
                        )
        except Exception as e:
            bqr.set_exception(str(e))
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        bqr.finish()
        return bqr

    ########## PRIVATE METHODS BELOW ##########

    def _valid_query(self, sparql) -> bool:
        if sparql == None:
            return False
        else:
            return "SELECT " in sparql.upper()

    def _reduce_query_results(self, result_rows):
        """
        Return a list of dictionary objects, one per result row,
        from the given list of <class 'rdflib.query.ResultRow'> objects.
        """
        reduced = list()
        if result_rows is not None:
            for result_row in result_rows:
                d = result_row.asdict()
                keys = list(d.keys())
                for key in keys:
                    d[key] = str(d[key])
                reduced.append(d)
        return reduced

    def _iterate_bom(self, i, bqr, libtype):
        # first determine the libs to visit
        unvisited = list()
        for libname in bqr.get_bom_libs_keys():
            if bqr.is_unvisited(libname):
                unvisited.append(libname)

        # then visit/query the unvisited libs
        for curr_lib in unvisited:
            rqr = self._execute_query(self._bom_sparql(curr_lib, libtype))
            logging.debug(json.dumps(rqr.data))
            if rqr.has_exception():
                bqr.set_lib_result(
                    curr_lib, "exception: {}".format(rqr.get_exception())
                )
            else:
                reduced = self._reduce_query_results(rqr.get_rows())
                bqr.set_lib_result(curr_lib, list())
                for obj in reduced:
                    used_lib = self._uriref_id(obj["used_lib"])
                    bqr.add_used_lib(curr_lib, used_lib)
                    bqr.add_unvisited(used_lib)

    def _bom_sparql(self, libname, libtype, limit=100):
        values = dict()
        values["libname"] = libname
        values["libtype"] = libtype
        values["limit"] = limit
        return SparqlTemplate().render("bill_of_materials.txt", values)

    def _execute_query(self, sparql) -> RdfQueryResult:
        """return a dict with a 'rows' key containing a list, and an optional 'exception' key containing a str"""
        rqr = RdfQueryResult(sparql)
        logging.debug("_execute_query: {}".format(sparql))
        if sparql == None:
            rqr.set_exception("the given sparql is None")
            return rqr
        try:
            for row in self.graph.query(sparql):
                rqr.add_row(
                    row
                )  # row is an instance of <class 'rdflib.query.ResultRow'>
        except Exception as e:
            rqr.set_exception(e)
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        rqr.finish()
        return rqr

    def _uriref_id(self, uriref):
        """
        For a rdflib.term.URIRef value like 'http://cosmosdb.com/caig/pypi_click' return 'pypi_click'.
        """
        return str(uriref).split("/")[-1]
