import asyncio
import json
import logging

import httpx

from src.services.ai_service import AiService
from src.services.db_service import DBService

from src.services.config_service import ConfigService
from src.services.ontology_service import OntologyService
from src.services.rag_data_result import RAGDataResult

from src.services.strategy_builder import StrategyBuilder


# Instances of this class are used to identify and retrieve system prompt data
# for the RAG pattern in a "OmniRAG" manner.  The RAG data will be read,
# per given user_text, from either:
# 1) Directly from Cosmos DB documents (DB RAG)
# 2) From Cosmos DB documents identified per an in-memory graph query (Graph RAG)
# 3) From Cosmos DB documents identified per a vector search to Cosmos (Vector RAG)
#
# Chris Joakim, Microsoft


class RAGDataService:

    def __init__(self, ai_svc: AiService, db_svc: DBService):
        try:
            self.ai_svc = ai_svc
            self.db_svc = db_svc
            self.owl = OntologyService().get_owl_content()
            # create a list of the attributes to include in the RAG data result
            self.doc_include_attributes = list()
            self.doc_include_attributes.append("libtype")
            self.doc_include_attributes.append("name")
            self.doc_include_attributes.append("summary")
            self.doc_include_attributes.append("documentation_summary")
            self.graph_source = str(ConfigService.graph_source())

            # web service authentication with shared secrets
            websvc_auth_header = ConfigService.websvc_auth_header()
            websvc_auth_value = ConfigService.websvc_auth_value()
            self.websvc_headers = dict()
            self.websvc_headers["Content-Type"] = "application/json"
            self.websvc_headers[websvc_auth_header] = websvc_auth_value
            logging.debug(
                "RAGDataService websvc_headers: {}".format(
                    json.dumps(self.websvc_headers, sort_keys=False)
                )
            )
        except Exception as e:
            logging.critical("Exception in RagDataService#__init__: {}".format(str(e)))

    async def get_rag_data(self, user_text, max_doc_count=3) -> RAGDataResult:
        """
        Return a RAGDataResult object which contains an array of the RAG
        documents to be used as a system prompt for a generative AI call
        to Azure OpenAI.  Each RAG document is a document from the Cosmos DB
        libraries collection.
        In this "OmniRAG" implementation, the RAG data will be read,
        per the given user_text, from one of either:
        1) Directly from Cosmos DB documents (DB RAG)
        2) From Cosmos DB documents identified per an in-memory graph query (Graph RAG)
        3) From Cosmos DB documents identified per a vector search to Cosmos (Vector RAG)
        """
        rdr = RAGDataResult()
        rdr.set_user_text(user_text)
        rdr.set_attr("max_doc_count", max_doc_count)

        rsb = StrategyBuilder(self.ai_svc)
        await rsb.initialize()
        strategy_obj = await rsb.determine(user_text)
        strategy = strategy_obj["strategy"]
        rdr.add_strategy(strategy)

        if strategy == "db":
            entitytype = strategy_obj["entitytype"]
            name = strategy_obj["name"]
            rdr.set_attr("entitytype", entitytype)
            rdr.set_attr("name", name)
            rag_docs_list = await self.get_database_rag_data(
                user_text, entitytype, name, max_doc_count, rdr
            )
            if len(rag_docs_list) == 0:
                # use a vector search if the db_search returns no results
                rdr.add_strategy("vector")
                rag_docs_list = await self.get_vector_rag_data(
                    user_text, max_doc_count, rdr
                )

        elif strategy == "graph":
            rag_docs_list = await self.get_graph_rag_data(user_text, rdr, max_doc_count)
            if len(rag_docs_list) == 0:
                # use a vector search if the graph_search returns no results
                rdr.add_strategy("vector")
                rag_docs_list = await self.get_vector_rag_data(
                    user_text, max_doc_count, rdr
                )
        else:
            # default to vector search
            rag_docs_list = await self.get_vector_rag_data(
                user_text, max_doc_count, rdr
            )

        # scrub the result docs of unnecessary attributes and make them
        # JSON serializable by removing _id
        for doc in rag_docs_list:
            attr_names = list(doc.keys())
            for attr_name in attr_names:
                if attr_name not in self.doc_include_attributes:
                    del doc[attr_name]
            rdr.add_doc(doc)

        rdr.finish()
        return rdr

    async def get_database_rag_data(
        self, user_text, libtype, name, max_doc_count, rdr: RAGDataResult
    ) -> list:
        rag_docs_list = list()
        try:
            logging.warning(
                "RagDataService#get_database_rag_data, libtype: {}, name: {}, user_text: {}".format(
                    name, name, user_text
                )
            )
            self.db_svc.set_db(ConfigService.graph_source_db())
            self.db_svc.set_coll(ConfigService.graph_source_container())
            docs = await self.db_svc.get_documents_by_libtype_and_names(libtype, [name])
            for doc in docs:
                if "_id" in doc.keys():
                    del doc["_id"]  # Mongo _id is not JSON serializable
            return docs

        except Exception as e:
            logging.critical(
                "Exception in RagDataService#get_database_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return rag_docs_list

    async def get_vector_rag_data(
        self, user_text, max_doc_count=3, rdr: RAGDataResult = None
    ) -> str:
        rag_docs_list = list()
        try:
            logging.warning(
                "RagDataService#get_vector_rag_data, user_text: {}".format(user_text)
            )
            rag_docs_list = list()
            create_embedding_response = self.ai_svc.generate_embeddings(user_text)
            embedding = create_embedding_response.data[0].embedding
            self.db_svc.set_db(ConfigService.graph_source_db())
            self.db_svc.set_coll(ConfigService.graph_source_container())
            vs_result = await self.db_svc.vector_search(embedding, k=max_doc_count)
            for vs_doc in vs_result["results"]:
                rag_docs_list.append(vs_doc)
        except Exception as e:
            logging.critical(
                "Exception in RagDataService#get_vector_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return rag_docs_list

    async def get_graph_rag_data(
        self, user_text, rdr: RAGDataResult, max_doc_count=6
    ) -> str:
        rag_docs_list = list()
        try:
            logging.warning(
                "RagDataService#get_graph_rag_data, user_text: {}".format(user_text)
            )
            # first generate and execute the SPARQL query vs the in-memory RDF graph
            info = dict()
            info["natural_language"] = user_text
            info["owl"] = self.owl
            sparql = self.ai_svc.generate_sparql_from_user_prompt(info)["sparql"]
            rdr.set_sparql(sparql)
            logging.info("get_graph_rag_data, sparql: {}".format(sparql))
            sparql_query_results = self._post_sparql_query_to_graph_microsvc(sparql)

            # iterate the SPARQL query results, collecting the libtype and names
            sparql_libtype_name_pairs = self._parse_sparql_rag_query_results(
                sparql_query_results
            )
            # query Cosmos DB using the graph-identified document libtype/libname coordinates
            self.db_svc.set_db(ConfigService.graph_source_db())
            self.db_svc.set_coll(ConfigService.graph_source_container())
            libtype, libnames = "pypi", list()
            for pair in sparql_libtype_name_pairs:
                libtype, name = pair[0], pair[1]
                libnames.append(name)
            docs = await self.db_svc.get_documents_by_libtype_and_names(
                libtype, libnames
            )
            for doc in docs:
                if "_id" in doc.keys():
                    del doc["_id"]  # Mongo _id is not JSON serializable
            return docs
        except Exception as e:
            logging.critical(
                "Exception in RagDataService#get_graph_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return rag_docs_list

    # ========== private methods below ==========

    def _parse_sparql_rag_query_results(self, sparql_query_results):
        # sparql_query_results looks like this:
        # {
        #     "sparql": "PREFIX caig: <http://cosmosdb.com/caig#> SELECT ?dependency WHERE { ?lib caig:ln 'flask' . ?lib caig:lt 'pypi' . ?lib caig:uses_lib ?dependency . }",
        #     "results": {
        #         "sparql": "PREFIX caig: <http://cosmosdb.com/caig#> SELECT ?dependency WHERE { ?lib caig:ln 'flask' . ?lib caig:lt 'pypi' . ?lib caig:uses_lib ?dependency . }",
        #         "results": [
        #             {
        #                 "dependency": "http://cosmosdb.com/caig/pypi_asgiref"
        #             },
        libtype_name_pairs = list()
        try:
            result_rows = sparql_query_results["results"]["results"]
            logging.warning(
                "sparql rag query result_rows count: {}".format(len(result_rows))
            )
            for result in result_rows:
                attr_key = sorted(result.keys())[0]
                # "dependency": "http://cosmosdb.com/caig/pypi_asgiref"
                value = result[attr_key]
                tokens = value.split("/")
                last_idx = len(tokens) - 1
                libtype_name = tokens[last_idx]
                pair = libtype_name.split("_")
                if len(pair) == 2:
                    libtype_name_pairs.append(pair)
        except Exception as e:
            logging.critical(
                "Exception in RagDataService#_parse_sparql_rag_query_results: {}".format(
                    str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return libtype_name_pairs

    def _post_sparql_query_to_graph_microsvc(self, sparql: str):
        """
        Execute a HTTP POST to the graph microservice with the given SPARQL query.
        Return the HTTP response JSON object.
        """
        try:
            url = self._graph_microsvc_sparql_query_url()
            postdata = dict()
            postdata["sparql"] = sparql
            r = httpx.post(
                url,
                headers=self.websvc_headers,
                data=json.dumps(postdata),
                timeout=30.0,
            )
            obj = json.loads(r.text)
            return obj
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
            return {}

    def _graph_microsvc_sparql_query_url(self):
        return "{}:{}/sparql_query".format(
            ConfigService.graph_service_url(), ConfigService.graph_service_port()
        )

    def using_nosql(self) -> str:
        return "cosmos_nosql" in self.graph_source
