import asyncio
import logging
import os
import time

import rdflib

from rdflib import Graph
from rdflib.namespace import Namespace

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.cosmos_vcore_service import CosmosVCoreService
from src.util.rdflib_triples_builder import RdflibTriplesBuilder
from src.util.counter import Counter
from src.util.fs import FS

# Instances of this class are used to build an instance of class GraphService,
# which contains an in-memory rdflib database.  The source data for building
# the graph consists of a Web Ontology File (OWL) and one of the following:
# 1) A RDF triples input file (i.e - *.nt)
# 2) A Cosmos DB Mongo vCore API account
# 3) A Cosmos DB NoSQL API account
#
# Methods here that use class CosmosNoSQLService and access Cosmos DB NoSQL are
# asynchronous and use the async/await keywords.
#
# Chris Joakim, Microsoft


class GraphBuilder:

    def __init__(self, opts={}):
        self.opts = opts
        self.graph_source = str(ConfigService().graph_source())
        self.vcore_svc = None
        self.nosql_svc = None

    async def initialize(self):
        try:
            self.dbname = ConfigService.graph_source_db()
            self.cname = ConfigService.graph_source_container()
            logging.warning(
                "GraphBuilder#initialize - dbname: {} cname: {}".format(
                    self.dbname, self.cname
                )
            )

            if self.graph_source == "cosmos_vcore":
                opts = dict()
                opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
                self.vcore_svc = CosmosVCoreService(opts)
                self.vcore_svc.set_db(self.dbname)
                self.vcore_svc.set_coll(self.cname)
                logging.info("GraphBuilder#initialize - vcore_svc created")

            elif self.graph_source == "cosmos_nosql":
                opts = dict()
                opts["enable_diagnostics_logging"] = False
                self.nosql_svc = CosmosNoSQLService(opts)
                await self.nosql_svc.initialize()
                logging.info("GraphBuilder#initialize - nosql_svc created")

        except Exception as e:
            logging.critical("GraphBuilder#initialize Exception:\n{}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    async def initialize_graph(self) -> rdflib.Graph:
        self.cns = self.graph_namespace()
        self.CNS = Namespace(self.cns)  # CNS ~ Custom Namespace
        logging.info("GraphBuilder#initialize_graph - cns: {}".format(self.cns))
        ontology_file = ConfigService.graph_source_owl_filename()
        logging.info(
            "GraphBuilder#initialize_graph - ontology_file: {}".format(ontology_file)
        )
        self.g = Graph()
        self.g.bind(self.graph_namespace_alias(), self.CNS)
        self.g.parse(ontology_file, format="xml")

    async def build(self, opts=None) -> rdflib.Graph:
        # Processing steps:
        # 1. Define the custom namespace, CNS
        # 2. Load the custom ontology file
        # 3. Bind that namespace to simply 'c' for brevity
        # 4. Display the defined classes and properties in the ontology
        # 5. Load the graph using the custom ontology

        await self.initialize_graph()
        if opts is not None:
            self.opts = opts

        config = ConfigService()
        logging.info("GraphBuilder#build graph_source: {}".format(self.graph_source))

        if self.graph_source == "rdf_file":
            self.populate_graph_from_rdf_file(self.g, config)
        elif self.graph_source == "json_file":
            self.populate_graph_from_json_file(self.g, config, self.CNS)
        elif self.graph_source == "cosmos_vcore":
            self.populate_graph_from_cosmosdb_vcore(self.g, config, self.CNS)
        elif self.graph_source == "cosmos_nosql":
            await self.populate_graph_from_cosmosdb_nosql(self.g, config, self.CNS)
        else:
            logging.critical(
                "WARNING: GraphBuilder defaulting to cosmos_vcore loading strategy"
            )
            self.populate_graph_from_cosmosdb_vcore(self.g, config, self.CNS)

        if "iterate_graph" in self.opts.keys():
            self.iterate_graph("after load")
        if "persist_graph" in self.opts.keys():
            self.persist_graph()
        return self.g

    def graph_namespace(self) -> str:
        """ " return a URI value like 'http://cosmosdb.com/caig#'"""
        return ConfigService.graph_namespace()

    def graph_namespace_alias(self) -> str:
        """ " return a value like 'caig' (from namespace 'http://cosmosdb.com/caig#')"""
        return ConfigService.graph_namespace_alias()

    def populate_graph_from_rdf_file(
        self, g: rdflib.Graph, config: ConfigService
    ) -> None:
        """Load the graph from a RDF (nt) triples file"""
        try:
            cwd = os.getcwd()
            rdf_file = config.graph_source_rdf_filename()
            fq_filename = "{}{}{}".format(cwd, os.sep, rdf_file)
            file_format = "nt"
            logging.info(
                "GraphBuilder#populate_graph_from_rdf_file: {}, format: {}".format(
                    fq_filename, file_format
                )
            )
            t1 = time.perf_counter()
            g.parse(fq_filename, format=file_format)
            t2 = time.perf_counter()
            seconds = f"{(t2 - t1):.9f}"
            logging.critical(
                "GraphBuilder#populate_graph_from_rdf_file - graph loaded in {}".format(
                    seconds
                )
            )
        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def populate_graph_from_cosmosdb_vcore(
        self, g: rdflib.Graph, config: ConfigService, CNS
    ) -> None:
        try:
            logging.info("GraphBuilder#populate_graph_from_cosmosdb_vcore")
            ns = self.graph_namespace().replace("#", "").strip()
            coll = self.vcore_svc.get_coll()
            docs_read = 0
            tb = RdflibTriplesBuilder()
            t1 = time.perf_counter()

            # Read the appropriate JSON documents from Cosmos DB, and pass
            # each to your RdflibTriplesBuilder to be added to the graph.
            for libtype in ["pypi"]:
                query_spec = {"libtype": libtype}
                projection = self.library_projection_attrs()
                cursor = coll.find(
                    query_spec, projection=projection, skip=0, limit=999999
                )
                for idx, doc in enumerate(cursor):
                    docs_read = docs_read + 1
                    if docs_read % 1000 == 0:
                        logging.info(
                            "GraphBuilder#populate_graph_from_cosmosdb_vcore - libdocs read: {}".format(
                                docs_read
                            )
                        )
                    tb.append_doc_to_graph(g, doc, CNS, ns)
            t2 = time.perf_counter()
            seconds = f"{(t2 - t1):.9f}"
            logging.critical(
                "GraphBuilder#populate_graph_from_cosmosdb_vcore - {} docs loaded into graph in {}".format(
                    docs_read, seconds
                )
            )
        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
            return None
        finally:
            self.vcore_svc.close()

    async def populate_graph_from_cosmosdb_nosql(
        self, g: rdflib.Graph, config: ConfigService, CNS
    ) -> None:
        try:
            logging.info("GraphBuilder#populate_graph_from_cosmosdb_nosql")
            dbproxy = self.nosql_svc.set_db(self.dbname)
            logging.info("dbproxy: {}".format(dbproxy))
            ctrproxy = self.nosql_svc.set_container(self.cname)
            logging.info("ctrproxy: {}".format(ctrproxy))

            ns = self.graph_namespace().replace("#", "").strip()
            tb = RdflibTriplesBuilder()
            t1 = time.perf_counter()

            # Read the appropriate JSON documents from Cosmos DB, and pass
            # each to your RdflibTriplesBuilder to be added to the graph.
            sql = "select c._id, c.name, c.libtype, c.license_kwds, c.kwds, c.developers, c.dependency_ids from c offset 0 limit 999999"
            query_results = ctrproxy.query_items(query=sql)
            docs_read = 0
            async for doc in query_results:
                docs_read = docs_read + 1
                if docs_read % 1000 == 0:
                    logging.info(
                        "GraphBuilder#populate_graph_from_cosmosdb_nosql - docs read: {}".format(
                            docs_read
                        )
                    )
                doc["id"] = doc["_id"]
                tb.append_doc_to_graph(g, doc, CNS, ns)

            t2 = time.perf_counter()
            seconds = f"{(t2 - t1):.9f}"
            logging.critical(
                "GraphBuilder#populate_graph_from_cosmosdb_nosql - {} docs loaded into graph in {}".format(
                    docs_read, seconds
                )
            )
        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
        finally:
            await self.nosql_svc.close()

    def populate_graph_from_json_file(
        self, g: rdflib.Graph, config: ConfigService, CNS
    ) -> None:
        try:
            logging.info("GraphBuilder#populate_graph_from_json_file")
            ns = self.graph_namespace().replace("#", "").strip()
            docs_read = 0
            t1 = time.perf_counter()
            label_counter = Counter()

            tb = RdflibTriplesBuilder()
            infile = self.opts["cosmos_documents_file"]
            vertices_list = FS.read_json(infile)
            for doc in vertices_list:
                label = doc["label"]
                label_counter.increment(label)
                docs_read = docs_read + 1
                tb.append_doc_to_graph(g, doc, CNS, ns)

            t2 = time.perf_counter()
            seconds = f"{(t2 - t1):.9f}"
            logging.critical(
                "GraphBuilder#populate_graph_from_json_file - {} docs loaded into graph in {}".format(
                    docs_read, seconds
                )
            )
            FS.write_json(label_counter.get_data(), "tmp/graph_builder_labels.json")

        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def library_projection_attrs(self):
        """
        The in-memory rdflib graph is built from these few Cosmos DB document attributes.
        See https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.find
        """
        return {
            "_id": 0,
            "libtype": 1,
            "id": 1,
            "name": 1,
            "kwds": 1,
            "license_kwds": 1,
            "developers": 1,
            "dependency_ids": 1,
        }

    def persist_graph(self):
        outfile = "tmp/graph_{}.nt".format(self.graph_source)
        logging.info("GraphBuilder#persist_graph start")
        t1 = time.perf_counter()
        self.g.serialize(format="nt", destination=outfile, encoding="utf-8")
        t2 = time.perf_counter()
        seconds = f"{(t2 - t1):.9f}"
        logging.critical(
            "GraphBuilder#persist_graph - graph written to file {} in {}".format(
                outfile, seconds
            )
        )

    def iterate_graph(self, comment):
        logging.info("GraphBuilder#iterate_graph start {} ...".format(comment))
        count = 0
        t1 = time.perf_counter()
        for s, p, o in self.g:  # Iterate the graph, counting the triples
            count = count + 1
        t2 = time.perf_counter()
        seconds = f"{(t2 - t1):.9f}"
        logging.critical(
            "GraphBuilder#iterate_graph completed, triples count: {} seconds: {}".format(
                count, seconds
            )
        )
